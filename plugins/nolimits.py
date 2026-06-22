"""Plugin: /nolimits
Usage:
  /nolimits on    — enable relaxed filters for this session
  /nolimits off   — disable relaxed filters
  /nolimits status — show current state

This toggles a per-session flag stored in `facts` as `nolimits_<session_id>`.
Relaxed mode bypasses heuristic response filters (length, repetition, coherence)
but still enforces a conservative safety blocklist to avoid producing illegal or dangerous instructions.
"""
COMMAND = "nolimits"
DESCRIPTION = "Toggle relaxed filtering for this session"

def run(args: str, session_id: str = None):
    from src import memory
    if not session_id:
        return "No session_id provided."
    arg = (args or "").strip().lower()
    key = f"nolimits_{session_id}"
    if arg in ("on", "enable", "1"):
        memory.save_facts({key: "1"})
        return "Relaxed filters enabled for this session. Safety blocklist remains active."
    if arg in ("off", "disable", "0"):
        memory.save_facts({key: "0"})
        return "Relaxed filters disabled for this session."
    if arg in ("status", "state", "?", "help"):
        facts = memory.get_all_facts()
        val = facts.get(key, "0")
        return f"Relaxed filters are {'ON' if val=='1' else 'OFF'} for this session."
    return "Usage: /nolimits on|off|status"
