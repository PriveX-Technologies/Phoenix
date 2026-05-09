import traceback
from flask import Flask, render_template, request, jsonify, send_from_directory
import os

app = Flask(__name__, template_folder='../frontend', static_folder='../frontend')
app.secret_key = os.urandom(24)

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


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)