"""
main.py  –  Phoenix launcher (Ollama / Qwen backend)

Starts the web UI directly – no training or dataset generation needed.
Ollama must be running with the Qwen model pulled before launching.

Quick-start:
    ollama pull qwen2.5
    ollama serve          # in a separate terminal (or it may already be running)
    python main.py
"""

import os
import sys
import time
import threading
import webbrowser
import subprocess

# ── Optional: override model via env ─────────────────────────────────────────
# OLLAMA_MODEL=qwen2.5:72b python main.py
model_name = os.environ.get("OLLAMA_MODEL", "qwen2.5")
host       = os.environ.get("OLLAMA_HOST",  "http://localhost:11434")

print("╔══════════════════════════════════════════╗")
print("║           Phoenix AI  –  Ollama           ║")
print("╚══════════════════════════════════════════╝")
print(f"  Backend : {host}")
print(f"  Model   : {model_name}")
print()

# ── Quick pre-flight: is Ollama reachable? ────────────────────────────────────
try:
    import requests
    r = requests.get(f"{host}/api/tags", timeout=3)
    tags = [m.get("name", "") for m in r.json().get("models", [])]
    if not any(model_name in t for t in tags):
        print(f"⚠️  Model '{model_name}' not found in Ollama.")
        print(f"   Run:  ollama pull {model_name}")
        print(f"   Available models: {tags or '(none)'}\n")
        # Continue anyway – inference.py will use rule-based fallback
    else:
        print(f"✅ Model '{model_name}' ready.\n")
except Exception as e:
    print(f"⚠️  Cannot reach Ollama at {host}: {e}")
    print("   Make sure Ollama is running:  ollama serve\n")
    # Continue – web UI will still start; error shown on /status

# ── Launch UI ─────────────────────────────────────────────────────────────────
print("🚀 Starting Phoenix Web UI...")

def open_browser():
    time.sleep(2)
    webbrowser.open("http://localhost:5000")

threading.Thread(target=open_browser, daemon=True).start()

try:
    subprocess.run([sys.executable, "src/web_ui.py"])
except KeyboardInterrupt:
    print("\n👋 Phoenix stopped.")
