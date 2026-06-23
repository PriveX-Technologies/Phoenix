"""
main.py  –  Phoenix launcher (Ollama / Qwen backend)

Quick-start:
    ollama pull qwen2.5
    ollama serve
    pip install -r requirements.txt
    python main.py

Optional features:
    Voice input:   pip install faster-whisper
    Fine-tune:     python fine_tune_ollama.py --status
"""

import os
import sys
import time
import threading
import webbrowser
import subprocess

model_name = os.environ.get("OLLAMA_MODEL", "qwen2.5")
host       = os.environ.get("OLLAMA_HOST",  "http://localhost:11434")

print("╔══════════════════════════════════════════╗")
print("║           Phoenix AI  –  Ollama          ║")
print("╚══════════════════════════════════════════╝")
print(f"  Backend : {host}")
print(f"  Model   : {model_name}")
print()

# ── Pre-flight checks ─────────────────────────────────────────────────────────
try:
    import requests

    # Ollama check
    r    = requests.get(f"{host}/api/tags", timeout=3)
    tags = [m.get("name", "") for m in r.json().get("models", [])]
    if not any(model_name in t for t in tags):
        print(f"⚠️  Model '{model_name}' not found.")
        print(f"   Run:  ollama pull {model_name}")
        print(f"   Available: {tags or '(none)'}\n")
    else:
        print(f"✅ Model '{model_name}' ready.")

    # Voice (optional)
    try:
        import faster_whisper  # noqa
        print("🎙️  Voice input ready  (faster-whisper)")
    except ImportError:
        print("ℹ️  Voice input disabled  (pip install faster-whisper to enable)")

    # Show loaded plugins
    import pathlib, importlib.util
    plugin_dir = pathlib.Path("plugins")
    plugins    = [p.stem for p in plugin_dir.glob("*.py") if p.stem != "__init__"]
    if plugins:
        print(f"🔌 Plugins: {', '.join('/' + p for p in plugins)}")

    print()

except Exception as e:
    print(f"⚠️  Cannot reach Ollama at {host}: {e}")
    print("   Make sure Ollama is running:  ollama serve\n")

# ── Launch UI ─────────────────────────────────────────────────────────────────
print("🚀 Starting Phoenix Web UI...")
print("   Visit: http://localhost:5000\n")

def open_browser():
    time.sleep(2)
    webbrowser.open("http://localhost:5000")

threading.Thread(target=open_browser, daemon=True).start()

try:
    subprocess.run([sys.executable, "src/web_ui.py"])
except KeyboardInterrupt:
    print("\n👋 Phoenix stopped.")
