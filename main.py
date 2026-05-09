import os
import sys
import time
import threading
import webbrowser
import subprocess

model_path = "models/phoenix.pt"
data_path  = "data/real_data.txt"

def data_exists():
    return os.path.exists(data_path) and os.path.getsize(data_path) > 0

def model_exists():
    return os.path.exists(model_path) and os.path.getsize(model_path) > 0

def run_script(script_path):
    try:
        subprocess.run([sys.executable, script_path], check=True)
    except subprocess.CalledProcessError:
        print(f"\n❌ Failed: {script_path}")
        sys.exit(1)

# Step 1: Dataset Check[cite: 3]
if not data_exists():
    print("📦 Generating dataset...")
    run_script("src/prepare_data.py")
else:
    count = sum(1 for _ in open(data_path, encoding="utf-8"))
    print(f"📦 Dataset ready ({count} pairs)")

# Step 2: Model Check[cite: 3]
if not model_exists():
    print("\n🔥 Training Phoenix...")
    run_script("src/train.py")
else:
    print("🧠 Model ready")

# Step 3: Launch UI[cite: 3]
print("\n🚀 Starting Phoenix Web UI...")

def open_browser():
    time.sleep(2)
    webbrowser.open("http://localhost:5000")

threading.Thread(target=open_browser, daemon=True).start()

try:
    # Use 'web_ui.py' verbatim as requested[cite: 3]
    subprocess.run([sys.executable, "src/web_ui.py"])
except KeyboardInterrupt:
    print("\n👋 Phoenix stopped.")