import traceback
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask import after_this_request
import os

app = Flask(__name__, template_folder='../frontend', static_folder='../frontend')
app.secret_key = os.urandom(24)

# ── CORS — allow the Phoenix HTML frontend (file:// or any origin) ────────────
@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

@app.route("/", defaults={"path": ""}, methods=["OPTIONS"])
@app.route("/<path:path>", methods=["OPTIONS"])
def options_handler(path):
    return "", 204

phoenix = None
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
            traceback.print_exc()   # ← prints the FULL stack trace to your terminal
            print(f"\n❌ inference.py failed to import: {e}\n")
    return phoenix, _load_error


# Eagerly load on startup so errors appear immediately in the terminal
get_phoenix()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/<path:path>")
def static_proxy(path):
    return send_from_directory(app.static_folder, path)


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
    """Return memory statistics from memory.py."""
    try:
        from memory import memory_stats
        return jsonify({"stats": memory_stats()})
    except Exception as e:
        return jsonify({"stats": {}, "error": str(e)})


@app.route("/memory")
def memory_turns():
    """Return recent conversation turns, optionally filtered by session."""
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
    """Clear the current session memory (keeps long-term facts)."""
    inf, err = get_phoenix()
    if err or inf is None:
        return jsonify({"ok": False, "error": "Model not loaded"})
    try:
        from memory import clear_session_memory
        clear_session_memory(inf.current_session)
        # Also reset turn counter on the inference module
        inf.turn_number = 0
        return jsonify({"ok": True, "session_id": inf.current_session})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)})


@app.route("/save", methods=["POST"])
def save_model():
    """Manually trigger a model checkpoint save."""
    inf, err = get_phoenix()
    if err or inf is None:
        return jsonify({"ok": False, "error": "Model not loaded"})
    try:
        inf.save_checkpoint()
        return jsonify({"ok": True, "message": "Checkpoint saved."})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)})


@app.route("/history")
def history():
    """Return full conversation history for the current session."""
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
    """Health check + model status endpoint."""
    inf, err = get_phoenix()
    lstm_ok   = inf is not None and inf.model is not None
    transf_ok = inf is not None and getattr(inf, "ft_model", None) is not None
    return jsonify({
        "ok":              err is None,
        "error":           err,
        "lstm_loaded":     lstm_ok,
        "transformer_loaded": transf_ok,
        "session_id":      getattr(inf, "current_session", None) if inf else None,
        "approved_count":  getattr(inf, "approved_count", 0)     if inf else 0,
    })


if __name__ == "__main__":
    print("\n🔥 Phoenix Web UI starting...")
    print("   Open phoenix.html in your browser, or visit http://localhost:5000")
    print("   Make sure train.py has been run to generate models/phoenix.pt\n")
    app.run(debug=False, host="0.0.0.0", port=5000)