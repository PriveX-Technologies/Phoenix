"""Plugin: /godmode
Usage:
  /godmode on    — enable per-session god mode (save every message)
  /godmode off   — disable god mode
  /godmode status — show current state

This plugin stores a small flag in the global facts table using the
key 'godmode_<session_id>' so the inference layer can persist every
turn while enabled.
"""
COMMAND = "godmode"
DESCRIPTION = "Toggle 'remember everything' (per-session)"

from datetime import datetime

def run(args: str, session_id: str = None):
    from src import memory
    if not session_id:
        return "No session_id provided."

    arg = (args or "").strip().lower()
    key = f"godmode_{session_id}"

    if arg in ("on", "enable", "1"):
        memory.save_facts({key: "1"})
        return "God mode enabled for this session. I'll remember everything."
    if arg in ("off", "disable", "0"):
        memory.save_facts({key: "0"})
        return "God mode disabled for this session."
    if arg in ("status", "state", "?", "help"):
        facts = memory.get_all_facts()
        val = facts.get(key, "0")
        return f"God mode is {'ON' if val=='1' else 'OFF'} for this session."

    return "Usage: /godmode on|off|status"
