import os

ROOT = "."

structure = {
    # Frontend
    "frontend": [
        "index.html",
        "style.css",
        "script.js"
    ],

    # AI Brain
    "brain": [
        "reasoning.py",
        "memory.py",
        "planner.py"
    ],

    # Voice System
    "voice": [
        "listen.py",
        "speak.py"
    ],

    # Vision System
    "vision": [
        "screen_capture.py",
        "detector.py"
    ],

    # Desktop Control
    "desktop": [
        "mouse.py",
        "keyboard.py",
        "windows.py"
    ],

    # Avatar System
    "avatar": [
        "emotions.py",
        "animation.py",
        "actions.py"
    ],

    # Future Expansion
    "ai": [
        "__init__.py"
    ],

    "plugins": [
        "__init__.py"
    ],

    "config": [
        "settings.py"
    ],

    "data": [
        ".gitkeep"
    ],

    "logs": [
        ".gitkeep"
    ],

    "models": [
        ".gitkeep"
    ],

    "skills": [
        "__init__.py"
    ],

    "tests": [
        "__init__.py"
    ]
}

# Create root
os.makedirs(ROOT, exist_ok=True)

# Root files
root_files = {
    "app.py": "# Phoenix Main Entry Point\n",
    "requirements.txt": "",
    "README.md": "# Phoenix\n",
    ".env": "",
    ".gitignore": """__pycache__/
*.pyc
.env
logs/
models/
"""
}

for filename, content in root_files.items():
    with open(os.path.join(ROOT, filename), "w", encoding="utf-8") as f:
        f.write(content)

# Create folders/files
for folder, files in structure.items():
    folder_path = os.path.join(ROOT, folder)
    os.makedirs(folder_path, exist_ok=True)

    for file in files:
        file_path = os.path.join(folder_path, file)

        if not os.path.exists(file_path):
            with open(file_path, "w", encoding="utf-8") as f:

                if file.endswith(".py"):
                    module = file.replace(".py", "")
                    f.write(f'"""\nPhoenix {module} module\n"""\n\n')

                elif file.endswith(".html"):
                    f.write("<!DOCTYPE html>\n<html></html>")

                elif file.endswith(".css"):
                    f.write("")

                elif file.endswith(".js"):
                    f.write("")

                else:
                    f.write("")

print("🔥 Phoenix Ultimate Structure Created!")