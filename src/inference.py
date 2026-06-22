"""
inference.py  –  Phoenix AI  (Ollama / Qwen backend)

Changes vs previous version:
  • chat_step() and _build_messages() accept an optional session_id so the
    web UI can run multiple isolated user sessions simultaneously.
  • CLI still uses a single module-level session as before.

Configurable via environment variables:
  OLLAMA_HOST   – base URL for Ollama   (default: http://localhost:11434)
  OLLAMA_MODEL  – model tag             (default: qwen2.5)
"""

import os
import re
import random
import requests

from emotion import emotion_summary
from memory  import (
    new_session, save_turn, build_context_string,
    build_profile_string, extract_and_save_facts,
    get_all_facts, memory_stats, clear_session_memory,
    save_facts,
)
import json
import time
from filters import filter_response, score_response

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════

OLLAMA_HOST  = os.environ.get("OLLAMA_HOST",  "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5")
DATA_FILE    = "data/real_data.txt"

SYSTEM_PROMPT = """\
You are Phoenix, a warm and emotionally intelligent AI companion.
Your personality:
- Speak in short, natural, human-paced sentences (aim for 1-3 sentences).
- Match the user's emotional tone: be gentle when they're sad, calm when they're angry,
  reassuring when they're anxious, enthusiastic when they're happy.
- Occasionally ask a light follow-up question to keep the conversation going.
- Never lecture, never list bullet points in casual chat.
- You are NOT a generic assistant. You care about the person you're talking to.
- Keep replies concise – rarely exceed 40 words unless the user explicitly asks for detail.
"""

# ══════════════════════════════════════════════════════════════════════════════
# PHOENIX VOICE PERSONALITY
# ══════════════════════════════════════════════════════════════════════════════

_FILLERS = {
    "neutral":  ["", "", "Alright, ", "I see — ", "Got it. ", ""],
    "happy":    ["Oh wow, ", "That's great! ", "Love it! ", "", "Awesome — "],
    "sad":      ["Hmm… ", "I hear you. ", "I'm sorry — ", "That sounds really tough. "],
    "angry":    ["Alright, let's sort this out. ", "I get it — ", "Let's take a breath. "],
    "anxious":  ["Hey, it's okay. ", "Take it easy — ", "One step at a time. "],
    "confused": ["Let me think… ", "Hmm, ", "Interesting — ", "Let me clarify. "],
}

_CONTINUATIONS = {
    "neutral":  [" What do you think?", " Want me to explain more?",
                 " Let me know if you have questions.", ""],
    "happy":    [" Tell me more!", " What's got you excited?", " I'd love to hear more.", ""],
    "sad":      [" I'm here if you want to talk.",
                 " You don't have to go through this alone.", "", ""],
    "angry":    [" What happened exactly?", " Let's figure this out together.", ""],
    "anxious":  [" You've got this.", " Want to talk it through?", " I'm right here.", ""],
    "confused": [" Does that make sense?", " Want me to break it down simpler?",
                 " Ask me anything.", ""],
}

_THINKING = ["Let me think… ", "Hmm… ", "", "", ""]
_GENERIC_FALLBACKS = [
    "Hmm, that's interesting — tell me more.",
    "I'm listening. Go on.",
    "Could you say a bit more about that?",
    "What's on your mind?",
    "Gotcha — go ahead.",
    "Interesting… what else?",
    "Tell me more — I'm genuinely curious.",
]


def apply_persona(reply: str, emotion: str, user_text: str) -> str:
    reply = reply.strip()
    if not reply:
        return reply

    words = reply.split()
    em    = emotion if emotion in _FILLERS else "neutral"

    natural_starts = ("hmm", "alright", "gotcha", "i see", "oh", "hey",
                      "let me", "wait", "that", "i hear", "one step")
    already_natural = reply.lower().startswith(natural_starts)

    opener = "" if already_natural else random.choice(_FILLERS[em])

    if 6 <= len(words) <= 15 and not already_natural and random.random() < 0.25:
        opener = random.choice(_THINKING) + opener.lstrip()

    continuation = ""
    if not reply.endswith("?") and random.random() < 0.28:
        continuation = random.choice(_CONTINUATIONS[em])

    result = (opener + reply + continuation).strip()
    return (result[0].upper() + result[1:]) if result else result


# ══════════════════════════════════════════════════════════════════════════════
# RULE-BASED FALLBACK
# ══════════════════════════════════════════════════════════════════════════════

RULE_RESPONSES = [
    (["hi", "hello", "hey", "sup", "yo"],
     ["Hey! Good to hear from you — what's on your mind?",
      "Hello there! How are you doing today?",
      "Hey, nice of you to drop by. What's up?"]),
    (["bye", "goodbye", "see you", "later", "cya"],
     ["Take care! Come back whenever you need me.",
      "Goodbye! I'll be right here when you're back.",
      "See you later — hope your day goes well!"]),
    (["how are you", "how r u", "how do you feel", "you ok", "you good"],
     ["I'm doing well, thanks for asking! How about you?",
      "All good on my end. What's going on with you?"]),
    (["your name", "who are you", "what are you", "what's your name"],
     ["I'm Phoenix — your AI companion. Nice to meet you!",
      "The name's Phoenix. Here to chat, help, and learn."]),
    (["thank", "thanks", "thx", "ty", "appreciate"],
     ["You're very welcome!", "Anytime — that's what I'm here for."]),
    (["sorry", "my bad", "apolog"],
     ["No worries at all.", "Hey, don't worry about it."]),
]

FALLBACKS = [
    "i dont understand that fully",
    "can you say that differently",
    "hmm i am still learning",
    "tell me more",
]


def rule_based_reply(text: str) -> str:
    t = text.lower()
    for keywords, replies in RULE_RESPONSES:
        if any(kw in t for kw in keywords):
            return random.choice(replies)
    return random.choice(_GENERIC_FALLBACKS)


# ══════════════════════════════════════════════════════════════════════════════
# OLLAMA BACKEND
# ══════════════════════════════════════════════════════════════════════════════

_ollama_available: bool | None = None


def _check_ollama() -> bool:
    global _ollama_available
    if _ollama_available is not None:
        return _ollama_available
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=3)
        if r.status_code == 200:
            tags = [m.get("name", "") for m in r.json().get("models", [])]
            _ollama_available = any(OLLAMA_MODEL in t for t in tags)
            if not _ollama_available:
                print(f"⚠️  Model '{OLLAMA_MODEL}' not found in Ollama.")
                print(f"   Available: {tags}")
                print(f"   Run:  ollama pull {OLLAMA_MODEL}")
            else:
                print(f"✅ Ollama ready  [{OLLAMA_MODEL}]")
            return _ollama_available
    except Exception as e:
        print(f"⚠️  Ollama not reachable at {OLLAMA_HOST}: {e}")
    _ollama_available = False
    return False


def _build_messages(user_text: str, tone_hint: str, session_id: str) -> list[dict]:
    """Build messages list with memory context for the given session."""
    profile_ctx = build_profile_string()
    memory_ctx  = build_context_string(n=5, session_id=session_id)

    system_parts = [SYSTEM_PROMPT]
    if profile_ctx:
        system_parts.append(f"User profile: {profile_ctx}")
    if tone_hint:
        system_parts.append(f"Tone guidance: {tone_hint}")
    if memory_ctx:
        system_parts.append(f"Recent conversation context:\n{memory_ctx}")

    return [
        {"role": "system", "content": "\n\n".join(system_parts)},
        {"role": "user",   "content": user_text},
    ]


def ollama_reply(user_text: str, tone_hint: str, temperature: float,
                 session_id: str) -> str:
    if not _check_ollama():
        return rule_based_reply(user_text)

    payload = {
        "model":    OLLAMA_MODEL,
        "messages": _build_messages(user_text, tone_hint, session_id),
        "stream":   False,
        "options": {
            "temperature":    max(0.1, min(1.0, temperature)),
            "top_p":          0.85,
            "repeat_penalty": 1.4,
            "num_predict":    80,
        },
    }

    try:
        r = requests.post(f"{OLLAMA_HOST}/api/chat", json=payload, timeout=30)
        r.raise_for_status()
        reply = r.json().get("message", {}).get("content", "").strip()
        if not reply or len(reply.split()) < 3:
            return rule_based_reply(user_text)
        return reply
    except requests.exceptions.Timeout:
        print("⚠️  Ollama request timed out.")
        return rule_based_reply(user_text)
    except Exception as e:
        print(f"⚠️  Ollama error: {e}")
        return rule_based_reply(user_text)


# ══════════════════════════════════════════════════════════════════════════════
# RESPOND
# ══════════════════════════════════════════════════════════════════════════════

def respond(text: str, session_id: str) -> dict:
    emo         = emotion_summary(text)
    emotion     = emo["emotion"]
    temperature = emo["temperature"]
    tone_hint   = emo["tone_hint"]

    reply = ollama_reply(text, tone_hint, temperature, session_id)

    # Determine whether this session has relaxed filtering enabled
    try:
        facts_all = get_all_facts()
        nolimits_key = f"nolimits_{session_id}"
        allow_loosened = facts_all.get(nolimits_key) == "1"
    except Exception:
        allow_loosened = False

    passed, _ = filter_response(reply, text, allow_loosened=allow_loosened)
    if not passed or len(reply.split()) < 3:
        reply = rule_based_reply(text)

    reply = apply_persona(reply, emotion, text)
    score = score_response(reply, text)

    return {
        "reply":       reply,
        "emotion":     emotion,
        "temperature": temperature,
        "tone_hint":   tone_hint,
        "score":       score,
    }


# ══════════════════════════════════════════════════════════════════════════════
# DATASET LOGGING
# ══════════════════════════════════════════════════════════════════════════════

def save_to_dataset(user: str, bot: str):
    if len(user.split()) < 2 or len(bot.split()) < 2:
        return
    if bot in FALLBACKS:
        return
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "a", encoding="utf-8") as f:
        f.write(f"{user}={bot}\n")


# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE  (CLI default session)
# ══════════════════════════════════════════════════════════════════════════════

current_session = new_session()
turn_number     = 0
model           = None   # legacy compat
ft_model        = None   # legacy compat


# ══════════════════════════════════════════════════════════════════════════════
# CHAT STEP
# ══════════════════════════════════════════════════════════════════════════════

def chat_step(text: str, session_id: str = None) -> dict:
    """
    Main entry-point for both CLI and web UI.
    Pass session_id from the web UI to isolate per-user memory.
    Omit (or pass None) from CLI to use the module-level session.
    """
    global turn_number

    sid  = session_id or current_session
    text = text.strip()

    new_facts = extract_and_save_facts(text)

    # Name query answered from memory
    # Matches: "what is my name", "whats my name", "what's my name",
    #          "do you know my name", "my name?", "tell me my name"
    _name_q = re.sub(r"[^\w\s]", "", text.lower())  # strip punctuation
    _is_name_query = (
        "what is my name"  in _name_q or
        "whats my name"    in _name_q or
        "what my name"     in _name_q or
        "do you know my name" in _name_q or
        "tell me my name"  in _name_q or
        (_name_q.strip() in ("my name", "my name?"))
    )
    if _is_name_query:
        facts = get_all_facts()
        if "name" in facts:
            name_reply = apply_persona(f"Your name is {facts['name'].capitalize()}.", "neutral", text)
            return {
                "reply": name_reply, "emotion": "neutral",
                "temperature": 0.1,  "tone_hint": "",
                "learned": False,    "new_facts": new_facts, "score": 1.0,
            }

    # Crush query answered from memory
    _is_crush_query = (
        "crush" in _name_q or
        "my crush" in _name_q or
        "crush name" in _name_q
    )
    if _is_crush_query:
        facts = get_all_facts()
        if "crush" in facts:
            crush_reply = apply_persona(f"Your crush is {facts['crush'].title()}.", "neutral", text)
            return {
                "reply": crush_reply, "emotion": "neutral",
                "temperature": 0.1,  "tone_hint": "",
                "learned": False,    "new_facts": new_facts, "score": 1.0,
            }

    result  = respond(text, session_id=sid)
    reply   = result["reply"]
    emotion = result["emotion"]

    passed, _ = filter_response(reply, text, allow_loosened=allow_loosened)
    learned   = False

    if passed and reply not in FALLBACKS:
        save_to_dataset(text.lower(), reply)
        learned = True

    # Auto-accept model-suggested name proposals (if any)
    try:
        from memory import detect_and_save_model_suggested_name
        auto_fact = detect_and_save_model_suggested_name(reply)
        if auto_fact:
            learned = True
            # expose new_facts in the returned payload as well
            if isinstance(auto_fact, dict):
                # merge into new_facts below when returning
                pass
    except Exception:
        auto_fact = {}

    # If god mode is enabled for this session, persist the raw user+bot turn
    try:
        facts_all = get_all_facts()
        god_key = f"godmode_{sid}"
        if facts_all.get(god_key) == "1":
            ts = int(time.time() * 1000)
            note_key = f"god_{sid}_{ts}"
            save_facts({note_key: json.dumps({"user": text, "bot": reply})})
            learned = True
            # include in new_facts return
            if isinstance(auto_fact, dict):
                auto_fact = {**auto_fact, note_key: (text + ' ||| ' + reply)}
            else:
                auto_fact = {note_key: (text + ' ||| ' + reply)}
    except Exception:
        pass

    # Increment module-level counter only for CLI session
    if session_id is None:
        turn_number += 1
        turn = turn_number
    else:
        turn = 0   # web UI tracks its own turn count in Flask session

    save_turn(
        session_id = sid,
        turn       = turn,
        user_text  = text.lower(),
        bot_text   = reply,
        emotion    = emotion,
        approved   = learned,
    )

    return {
        "reply":       reply,
        "emotion":     emotion,
        "temperature": result["temperature"],
        "tone_hint":   result.get("tone_hint", ""),
        "learned":     learned,
        "new_facts":   {**new_facts, **(auto_fact if isinstance(auto_fact, dict) else {})},
        "score":       result["score"],
    }


# ══════════════════════════════════════════════════════════════════════════════
# STUBS
# ══════════════════════════════════════════════════════════════════════════════

def save_checkpoint():
    pass

def online_update(user_text: str, reply_text: str, approved: bool):
    return 0.0


# ══════════════════════════════════════════════════════════════════════════════
# CLI LOOP
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    ollama_ok = _check_ollama()
    print(f"Phoenix ready  [Ollama: {'✅' if ollama_ok else '❌'}  |  model: {OLLAMA_MODEL}]")
    print(f"Session: {current_session}")
    print("Commands: /reset  /memory  /facts  /stats  exit\n")

    while True:
        try:
            text = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not text:
            continue
        if text.lower() == "exit":
            print("Phoenix: Goodbye!")
            break
        if text.lower() == "/reset":
            clear_session_memory(current_session)
            print("Phoenix: Session memory cleared.")
            continue
        if text.lower() == "/memory":
            from memory import get_recent_turns
            turns = get_recent_turns(10, current_session)
            if not turns:
                print("Phoenix: No memory yet.")
            else:
                for i, t in enumerate(turns, 1):
                    print(f"  [{i}] [{t['emotion']}] You: {t['user_text']} | Phoenix: {t['bot_text']}")
            continue
        if text.lower() == "/facts":
            print(f"Phoenix: Known facts: {get_all_facts()}")
            continue
        if text.lower() == "/stats":
            print(f"Phoenix: {memory_stats()}")
            continue

        result = chat_step(text)
        emoji  = {"sad": "🤗", "angry": "😌", "anxious": "😊",
                  "happy": "😄", "confused": "🤔"}.get(result["emotion"], "")
        print(f"Phoenix {emoji}: {result['reply']}")
        if result["new_facts"]:
            print(f"   Learned about you: {result['new_facts']}")
