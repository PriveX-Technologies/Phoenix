"""
web_ui.py  –  Phoenix Flask server with voice integration

Features:
  • Multi-user sessions (each browser tab gets isolated context)
  • Voice input transcription via /voice endpoint (faster-whisper)
  • Voice output with emotion-aware modifiers
  • Plugin system with command routing
  • Error recovery and fallback handling
"""

import traceback
import uuid
import os
from flask import Flask, render_template, request, jsonify, send_from_directory, session

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))

app = Flask(__name__, template_folder=FRONTEND_DIR, static_folder=FRONTEND_DIR)
app.secret_key = os.environ.get("PHOENIX_SECRET", os.urandom(24))

# ── CORS ──────────────────────────────────────────────────────────────────────
@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

@app.route("/", defaults={"path": ""}, methods=["OPTIONS"])
@app.route("/<path:path>",             methods=["OPTIONS"])
def options_handler(path):
    return "", 204

# ── Inference lazy-load ───────────────────────────────────────────────────────
phoenix     = None
_load_error = None

def get_phoenix():
    global phoenix, _load_error
    if phoenix is None and _load_error is None:
        try:
            import inference as _inf
            phoenix = _inf
            print("✅ inference module loaded.")
        except Exception as e:
            _load_error = str(e)
            traceback.print_exc()
    return phoenix, _load_error

get_phoenix()

# ── Voice modules ─────────────────────────────────────────────────────────────
try:
    import listen
    import speak
    VOICE_AVAILABLE = listen.get_whisper_available()
except ImportError as e:
    print(f"⚠️  Voice modules not available: {e}")
    VOICE_AVAILABLE = False

# ── Plugin loader ─────────────────────────────────────────────────────────────
import importlib.util, pathlib

_plugins: dict = {}

def load_plugins():
    """Load all .py files from plugins/ directory."""
    plugin_dir = pathlib.Path(__file__).parent.parent / "plugins"
    plugin_dir.mkdir(exist_ok=True)
    for path in plugin_dir.glob("*.py"):
        name = path.stem
        try:
            spec   = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, "COMMAND") and hasattr(module, "run"):
                _plugins[module.COMMAND] = module
                print(f"🔌 Plugin loaded: /{module.COMMAND}")
        except Exception as e:
            print(f"⚠️  Plugin '{name}' failed to load: {e}")

load_plugins()

# ── Multi-user session helpers ────────────────────────────────────────────────
def _get_user_session_id() -> str:
    """Return (creating if needed) a stable session_id for this browser tab."""
    if "phoenix_session_id" not in session:
        session["phoenix_session_id"] = f"web_{uuid.uuid4().hex[:12]}"
    return session["phoenix_session_id"]

def _get_user_turn() -> int:
    return session.get("turn_number", 0)

def _inc_user_turn():
    session["turn_number"] = session.get("turn_number", 0) + 1
    return session["turn_number"]

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    _get_user_session_id()   # initialise cookie on first visit
    return render_template("index.html")

@app.route("/assets/3dModel/cyber_samurai.glb")
def serve_glb():
    return send_from_directory(
        os.path.join(FRONTEND_DIR, "assets", "3dModel"),
        "cyber_samurai.glb", mimetype="model/gltf-binary"
    )

@app.route("/<path:path>")
def static_proxy(path):
    return send_from_directory(FRONTEND_DIR, path)


# ── /chat ─────────────────────────────────────────────────────────────────────
@app.route("/chat", methods=["POST"])
def chat():
    data       = request.get_json()
    text       = data.get("message", "").strip()
    allow_loosened = data.get("allow_loosened", False)
    session_id = _get_user_session_id()

    if not text:
        return jsonify({"error": "Empty message"}), 400

    inf, err = get_phoenix()
    if err or inf is None:
        return jsonify({"error": f"Model not loaded: {err}"}), 500

    # Check for plugin command  (/pluginname args…)
    if text.startswith("/"):
        parts   = text[1:].split(None, 1)
        cmd     = parts[0].lower()
        args    = parts[1] if len(parts) > 1 else ""
        if cmd in _plugins:
            try:
                reply = _plugins[cmd].run(args, session_id=session_id)
                return jsonify({
                    "reply": reply,
                    "emotion": "neutral",
                    "tone_hint": "",
                    "learned": False,
                    "new_facts": {},
                    "score": 1.0
                })
            except Exception as e:
                return jsonify({"error": f"Plugin error: {e}"}), 500

    try:
        # Pass per-user session_id into chat_step
        result = inf.chat_step(text, session_id=session_id,
                               allow_loosened=allow_loosened)
        _inc_user_turn()
        
        # Include TTS payload if speak module available
        tts_payload = None
        if VOICE_AVAILABLE:
            try:
                voice_config = data.get("voice_config")
                tts_payload = speak.format_tts_payload(
                    result["reply"],
                    emotion=result.get("emotion", "neutral"),
                    voice_config=voice_config
                )
            except Exception as e:
                print(f"⚠️  TTS payload error: {e}")
        
        response = {
            "reply":     result["reply"],
            "emotion":   result.get("emotion", "neutral"),
            "tone_hint": result.get("tone_hint", ""),
            "learned":   result.get("learned", False),
            "new_facts": result.get("new_facts", {}),
            "score":     result.get("score", 0),
        }
        
        if tts_payload:
            response["tts"] = tts_payload
        
        return jsonify(response)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Generation error: {e}"}), 500


# ── /voice  (Phase 5.2 — Whisper transcription + TTS) ────────────────────────
@app.route("/voice", methods=["POST"])
def voice():
    """
    Accepts a WAV/WebM audio file, transcribes with faster-whisper,
    then runs it through /chat automatically.

    curl -X POST http://localhost:5000/voice \
         -F "audio=@recording.wav"
    """
    if not VOICE_AVAILABLE:
        return jsonify({
            "error": "Voice transcription not available",
            "fix": "pip install faster-whisper"
        }), 501

    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    session_id = _get_user_session_id()
    audio_file = request.files["audio"]
    tmp_path   = f"/tmp/phoenix_voice_{uuid.uuid4().hex}.wav"
    
    try:
        # Save temp audio file
        audio_file.save(tmp_path)
        
        # Transcribe audio
        transcript, meta = listen.transcribe_audio(
            tmp_path,
            language="en",
            confidence_threshold=0.5
        )
        
        if not transcript:
            error_msg = meta.get("error", "Unknown transcription error")
            fallback = listen.get_fallback_response()
            
            return jsonify({
                "error": error_msg,
                "transcript": "",
                "fallback_reply": fallback,
                "metadata": meta
            }), 422
        
        # Process transcribed text through chat
        inf, err = get_phoenix()
        if err or inf is None:
            return jsonify({
                "transcript": transcript,
                "error": f"Model not loaded: {err}"
            }), 500
        
        # Chat with voice flag (loosened filtering)
        result = inf.chat_step(
            transcript,
            session_id=session_id,
            allow_loosened=True  # Voice input is usually looser
        )
        _inc_user_turn()
        
        # Build response with TTS
        tts_payload = None
        if VOICE_AVAILABLE:
            try:
                tts_payload = speak.format_tts_payload(
                    result["reply"],
                    emotion=result.get("emotion", "neutral")
                )
            except Exception as e:
                print(f"⚠️  TTS payload error: {e}")
        
        response = {
            "transcript": transcript,
            "reply":      result["reply"],
            "emotion":    result.get("emotion", "neutral"),
            "tone_hint":  result.get("tone_hint", ""),
            "learned":    result.get("learned", False),
            "new_facts":  result.get("new_facts", {}),
            "score":      result.get("score", 0),
            "confidence": meta.get("confidence", 0),
            "metadata":   meta,
        }
        
        if tts_payload:
            response["tts"] = tts_payload
        
        return jsonify(response)
        
    except Exception as e:
        print(f"❌ Voice endpoint error: {e}")
        traceback.print_exc()
        return jsonify({
            "error": f"Voice processing failed: {str(e)}",
            "fallback_reply": listen.get_fallback_response()
        }), 500
    
    finally:
        # Clean up temp file
        try:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except Exception as e:
            print(f"⚠️  Temp file cleanup error: {e}")


# ── /plugins  (list available plugins) ───────────────────────────────────────
@app.route("/plugins")
def list_plugins():
    return jsonify({
        "plugins": [
            {
                "command": f"/{cmd}",
                "description": getattr(mod, "DESCRIPTION", ""),
                "usage": getattr(mod, "USAGE", f"/{cmd} [args]")
            }
            for cmd, mod in _plugins.items()
        ]
    })


# ── Original endpoints (unchanged) ───────────────────────────────────────────

@app.route("/facts")
def facts():
    inf, err = get_phoenix()
    if err or inf is None:
        return jsonify({"facts": {}})
    try:
        from memory import get_all_facts
        return jsonify({"facts": get_all_facts()})
    except Exception:
        return jsonify({"facts": {}})

@app.route("/stats")
def stats():
    try:
        from memory import memory_stats
        return jsonify({"stats": memory_stats()})
    except Exception as e:
        return jsonify({"stats": {}, "error": str(e)})

@app.route("/memory")
def memory_turns():
    session_id = request.args.get("session_id", _get_user_session_id())
    n          = int(request.args.get("n", 20))
    try:
        from memory import get_recent_turns
        return jsonify({"turns": get_recent_turns(n=n, session_id=session_id)})
    except Exception as e:
        return jsonify({"turns": [], "error": str(e)})

@app.route("/reset_session", methods=["POST"])
def reset_session():
    inf, err = get_phoenix()
    if err or inf is None:
        return jsonify({"ok": False, "error": "Model not loaded"})
    try:
        from memory import clear_session_memory
        sid = _get_user_session_id()
        clear_session_memory(sid)
        session["turn_number"] = 0
        return jsonify({"ok": True, "session_id": sid})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)})

@app.route("/save", methods=["POST"])
def save_model():
    return jsonify({"ok": True, "message": "Ollama backend – no checkpoint to save."})

@app.route("/history")
def history():
    inf, err = get_phoenix()
    if err or inf is None:
        return jsonify({"history": []})
    try:
        from memory import get_recent_turns
        sid   = _get_user_session_id()
        turns = get_recent_turns(n=100, session_id=sid)
        return jsonify({"history": turns, "session_id": sid,
                        "turn_count": _get_user_turn()})
    except Exception as e:
        return jsonify({"history": [], "error": str(e)})

@app.route("/status")
def status():
    inf, err   = get_phoenix()
    ollama_ok  = False
    ollama_mdl = "unknown"
    if inf is not None:
        try:
            ollama_ok  = inf._check_ollama()
            ollama_mdl = inf.OLLAMA_MODEL
        except Exception:
            pass
    
    return jsonify({
        "ok":                 err is None,
        "error":              err,
        "backend":            "ollama",
        "ollama_ready":       ollama_ok,
        "model":              ollama_mdl,
        "lstm_loaded":        False,
        "transformer_loaded": False,
        "session_id":         _get_user_session_id(),
        "turn_count":         _get_user_turn(),
        "plugins_loaded":     list(_plugins.keys()),
        "voice_available":    VOICE_AVAILABLE,
    })


if __name__ == "__main__":
    print("\n🔥 Phoenix Web UI (multi-user · voice · plugins)")
    print(f"   Frontend : {FRONTEND_DIR}")
    print(f"   Plugins  : {list(_plugins.keys()) or 'none'}")
    print(f"   Voice    : {'✅ enabled' if VOICE_AVAILABLE else '⚠️  disabled'}")
    print("   Visit    : http://localhost:5000\n")
    app.run(debug=False, host="0.0.0.0", port=5000)