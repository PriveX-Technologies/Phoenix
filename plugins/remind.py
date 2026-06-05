"""
plugins/remind.py  –  Phoenix Plugin
Saves a quick reminder to a local file and lists them.
Usage:
  /remind buy milk at 6pm       → saves reminder
  /remind list                  → shows all reminders
  /remind clear                 → clears all reminders
"""

import json, pathlib
from datetime import datetime

COMMAND     = "remind"
DESCRIPTION = "Save and view quick reminders"
USAGE       = "/remind <text>  |  /remind list  |  /remind clear"

REMINDERS_FILE = pathlib.Path("data/reminders.json")


def _load() -> list:
    if REMINDERS_FILE.exists():
        try:
            return json.loads(REMINDERS_FILE.read_text())
        except Exception:
            pass
    return []


def _save(items: list):
    REMINDERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    REMINDERS_FILE.write_text(json.dumps(items, indent=2))


def run(args: str, session_id: str = None) -> str:
    args = args.strip()

    if not args or args.lower() == "list":
        items = _load()
        if not items:
            return "No reminders saved. Add one with /remind <text>"
        lines = "\n".join(
            f"  [{i+1}] {r['text']}  (saved {r['at']})"
            for i, r in enumerate(items)
        )
        return f"📋 Your reminders:\n{lines}"

    if args.lower() == "clear":
        _save([])
        return "✅ All reminders cleared."

    items = _load()
    items.append({
        "text":       args,
        "at":         datetime.now().strftime("%Y-%m-%d %H:%M"),
        "session_id": session_id or "cli",
    })
    _save(items)
    return f"✅ Reminder saved: \"{args}\"\n   You have {len(items)} reminder(s). Type /remind list to view."
