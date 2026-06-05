import traceback
from flask import Flask, render_template, request, jsonify, send_from_directory
import os

# frontend/ lives one level up from src/
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend')
FRONTEND_DIR = os.path.abspath(FRONTEND_DIR)

app = Flask(__name__, template_folder=FRONTEND_DIR, static_folder=FRONTEND_DIR)
app.secret_key = os.urandom(24)

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

# ── Model lazy-load ───────────────────────────────────────────────────────────
phoenix     = None
_load_error = None

def get_phoenix():
    global phoenix, _load_error
    if phoenix is None and _load_error is None:
        try:
            import inference as _inf
            phoenix = _inf
            print("✅ inference module loaded successfully.")
        except Exception as e:
            _load_error = str(e)
            traceback.print_exc()
            print(f"\n❌ inference.py failed to import: {e}\n")
    return phoenix, _load_error

get_phoenix()   # eager load on startup

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/assets/3dModel/cyber_samurai.glb")
def serve_glb():
    return send_from_directory(
        os.path.join(FRONTEND_DIR, "assets", "3dModel"),
        "cyber_samurai.glb",
        mimetype="model/gltf-binary"
    )


@app.route("/<path:path>")
def static_proxy(path):
    return send_from_directory(FRONTEND_DIR, path)


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    text = data.get("message", "").strip()
    if not text:
        return jsonify({"error": "Empty message"}), 400

    inf, err = get_phoenix()
    if err or inf is None:
        return jsonify({"error": f"Model not loaded: {err}"}), 500

    try:
        result = inf.chat_step(text)
        return jsonify({
            "reply":     result["reply"],
            "emotion":   result["emotion"],
            "tone_hint": result.get("tone_hint", ""),
            "learned":   result["learned"],
            "new_facts": result.get("new_facts", {}),
            "score":     result.get("score", 0),
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Generation error: {e}"}), 500


@app.route("/facts")
def facts():
    inf, err = get_phoenix()
    if err or inf is None:
        return jsonify({"facts": {}})
    from memory import get_all_facts
    return jsonify({"facts": get_all_facts()})


@app.route("/stats")
def stats():
    try:
        from memory import memory_stats
        return jsonify({"stats": memory_stats()})
    except Exception as e:
        return jsonify({"stats": {}, "error": str(e)})


@app.route("/memory")
def memory_turns():
    session_id = request.args.get("session_id", None)
    n          = int(request.args.get("n", 20))
    try:
        from memory import get_recent_turns
        turns = get_recent_turns(n=n, session_id=session_id)
        return jsonify({"turns": turns})
    except Exception as e:
        return jsonify({"turns": [], "error": str(e)})


@app.route("/reset_session", methods=["POST"])
def reset_session():
    inf, err = get_phoenix()
    if err or inf is None:
        return jsonify({"ok": False, "error": "Model not loaded"})
    try:
        from memory import clear_session_memory
        clear_session_memory(inf.current_session)
        inf.turn_number = 0
        return jsonify({"ok": True, "session_id": inf.current_session})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)})


@app.route("/save", methods=["POST"])
def save_model():
    """No-op for Ollama backend – weights are managed by Ollama."""
    return jsonify({"ok": True, "message": "Ollama backend – no checkpoint to save."})


@app.route("/history")
def history():
    inf, err = get_phoenix()
    if err or inf is None:
        return jsonify({"history": []})
    try:
        from memory import get_recent_turns
        turns = get_recent_turns(n=100, session_id=inf.current_session)
        return jsonify({
            "history":    turns,
            "session_id": inf.current_session,
            "turn_count": inf.turn_number,
        })
    except Exception as e:
        return jsonify({"history": [], "error": str(e)})


@app.route("/status")
def status():
    inf, err = get_phoenix()

    # Check Ollama availability
    ollama_ok    = False
    ollama_model = "unknown"
    if inf is not None:
        try:
            ollama_ok    = inf._check_ollama()
            ollama_model = inf.OLLAMA_MODEL
        except Exception:
            pass

    return jsonify({
        "ok":              err is None,
        "error":           err,
        "backend":         "ollama",
        "ollama_ready":    ollama_ok,
        "model":           ollama_model,
        # Legacy keys kept so existing frontend code doesn't break
        "lstm_loaded":     False,
        "transformer_loaded": False,
        "session_id":      getattr(inf, "current_session", None) if inf else None,
        "approved_count":  getattr(inf, "turn_number",     0)    if inf else 0,
    })


if __name__ == "__main__":
    print("\n🔥 Phoenix Web UI starting (Ollama / Qwen backend)...")
    print(f"   Serving frontend from: {FRONTEND_DIR}")
    print("   Visit: http://localhost:5000\n")
    app.run(debug=False, host="0.0.0.0", port=5000)
