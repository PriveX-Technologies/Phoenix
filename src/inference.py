"""
inference.py  –  Phoenix AI  (Ollama / Qwen backend)

Replaces the original LSTM + fine-tuned-transformer pipeline with a call to
a locally-running Ollama server.  All other Phoenix systems (persona, emotion
detection, memory, filters, online dataset logging) are kept intact.

Requirements
------------
  pip install requests
  ollama pull qwen2.5          # or whichever Qwen tag you prefer
  ollama serve                 # running on localhost:11434 (default)

Configurable via environment variables:
  OLLAMA_HOST   – base URL for Ollama   (default: http://localhost:11434)
  OLLAMA_MODEL  – model tag             (default: qwen2.5)
"""

import os
import random
import requests
import json

from emotion import emotion_summary
from memory  import (
    new_session, save_turn, build_context_string,
    build_profile_string, extract_and_save_facts,
    get_all_facts, memory_stats, clear_session_memory,
)
from filters import filter_response, score_response

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════

OLLAMA_HOST  = os.environ.get("OLLAMA_HOST",  "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5")

DATA_FILE    = "data/real_data.txt"

# ── Phoenix system prompt ─────────────────────────────────────────────────────
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
# PHOENIX VOICE PERSONALITY  (unchanged from original)
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
    """Post-process any reply to match the Phoenix voice personality."""
    reply = reply.strip()
    if not reply:
        return reply

    words = reply.split()
    em    = emotion if emotion in _FILLERS else "neutral"

    natural_starts = ("hmm", "alright", "gotcha", "i see", "oh", "hey",
                      "let me", "wait", "that", "i hear", "one step")
    already_natural = reply.lower().startswith(natural_starts)

    opener = ""
    if not already_natural:
        opener = random.choice(_FILLERS[em])

    if 6 <= len(words) <= 15 and not already_natural and random.random() < 0.25:
        opener = random.choice(_THINKING) + opener.lstrip()

    continuation = ""
    if not reply.endswith("?") and random.random() < 0.28:
        continuation = random.choice(_CONTINUATIONS[em])

    result = (opener + reply + continuation).strip()
    if result:
        result = result[0].upper() + result[1:]
    return result


# ══════════════════════════════════════════════════════════════════════════════
# RULE-BASED FALLBACK  (kept as safety net, unchanged)
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


def rule_based_reply(text: str) -> str:
    t = text.lower()
    for keywords, replies in RULE_RESPONSES:
        if any(kw in t for kw in keywords):
            return random.choice(replies)
    return random.choice(_GENERIC_FALLBACKS)


# ══════════════════════════════════════════════════════════════════════════════
# OLLAMA / QWEN BACKEND
# ══════════════════════════════════════════════════════════════════════════════

# Cached availability flag so we only probe once per process startup
_ollama_available: bool | None = None


def _check_ollama() -> bool:
    """Return True if Ollama is reachable and the configured model is present."""
    global _ollama_available
    if _ollama_available is not None:
        return _ollama_available
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=3)
        if r.status_code == 200:
            tags = [m.get("name", "") for m in r.json().get("models", [])]
            # Match on model name prefix (e.g. "qwen2.5" matches "qwen2.5:latest")
            _ollama_available = any(OLLAMA_MODEL in t for t in tags)
            if not _ollama_available:
                print(f"⚠️  Ollama is running but model '{OLLAMA_MODEL}' not found.")
                print(f"   Available: {tags}")
                print(f"   Run:  ollama pull {OLLAMA_MODEL}")
            else:
                print(f"✅ Ollama ready  [{OLLAMA_MODEL}]")
            return _ollama_available
    except Exception as e:
        print(f"⚠️  Ollama not reachable at {OLLAMA_HOST}: {e}")
    _ollama_available = False
    return False


def _build_messages(user_text: str, tone_hint: str) -> list[dict]:
    """
    Construct the messages list for the Ollama /api/chat endpoint.
    Injects memory context and tone hint into the system turn.
    """
    profile_ctx = build_profile_string()
    memory_ctx  = build_context_string(n=5, session_id=current_session)

    system_parts = [SYSTEM_PROMPT]
    if profile_ctx:
        system_parts.append(f"User profile: {profile_ctx}")
    if tone_hint:
        system_parts.append(f"Tone guidance: {tone_hint}")
    if memory_ctx:
        system_parts.append(f"Recent conversation context:\n{memory_ctx}")

    messages = [
        {"role": "system",    "content": "\n\n".join(system_parts)},
        {"role": "user",      "content": user_text},
    ]
    return messages


def ollama_reply(user_text: str, tone_hint: str, temperature: float) -> str:
    """
    Call Ollama's chat API and return the assistant's reply text.
    Falls back to rule_based_reply on any error.
    """
    if not _check_ollama():
        return rule_based_reply(user_text)

    payload = {
        "model":    OLLAMA_MODEL,
        "messages": _build_messages(user_text, tone_hint),
        "stream":   False,
        "options": {
            "temperature":      max(0.1, min(1.0, temperature)),
            "top_p":            0.85,
            "repeat_penalty":   1.4,
            "num_predict":      80,   # max tokens in reply
        },
    }

    try:
        r = requests.post(
            f"{OLLAMA_HOST}/api/chat",
            json=payload,
            timeout=30,
        )
        r.raise_for_status()
        data  = r.json()
        reply = data.get("message", {}).get("content", "").strip()

        if not reply:
            return rule_based_reply(user_text)

        # Basic quality gate: reject if reply is suspiciously short
        if len(reply.split()) < 3:
            return rule_based_reply(user_text)

        return reply

    except requests.exceptions.Timeout:
        print("⚠️  Ollama request timed out.")
        return rule_based_reply(user_text)
    except Exception as e:
        print(f"⚠️  Ollama error: {e}")
        return rule_based_reply(user_text)


# ══════════════════════════════════════════════════════════════════════════════
# RESPOND  (main generation entry-point)
# ══════════════════════════════════════════════════════════════════════════════

def respond(text: str) -> dict:
    emo         = emotion_summary(text)
    emotion     = emo["emotion"]
    temperature = emo["temperature"]
    tone_hint   = emo["tone_hint"]

    reply = ollama_reply(text, tone_hint, temperature)

    # Validate; if garbage, fall back to rule-based
    passed, _ = filter_response(reply, text)
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
# DATASET LOGGING  (unchanged – keeps training data growing)
# ══════════════════════════════════════════════════════════════════════════════

FALLBACKS = [
    "i dont understand that fully",
    "can you say that differently",
    "hmm i am still learning",
    "tell me more",
]


def save_to_dataset(user: str, bot: str):
    if len(user.split()) < 2 or len(bot.split()) < 2:
        return
    if bot in FALLBACKS:
        return
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "a", encoding="utf-8") as f:
        f.write(f"{user}={bot}\n")


# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════

current_session = new_session()
turn_number     = 0

# These are kept for API compatibility with web_ui.py
model           = None   # no LSTM
ft_model        = None   # no transformer


# ══════════════════════════════════════════════════════════════════════════════
# CHAT STEP  (used by both CLI and web_ui.py)
# ══════════════════════════════════════════════════════════════════════════════

def chat_step(text: str) -> dict:
    global turn_number

    text      = text.strip()
    new_facts = extract_and_save_facts(text)

    # Special: name query answered from memory
    if "what is my name" in text.lower():
        facts = get_all_facts()
        if "name" in facts:
            name_reply = apply_persona(f"your name is {facts['name']}", "neutral", text)
            return {
                "reply":       name_reply,
                "emotion":     "neutral",
                "temperature": 0.1,
                "tone_hint":   "",
                "learned":     False,
                "new_facts":   new_facts,
                "score":       1.0,
            }

    result  = respond(text)
    reply   = result["reply"]
    emotion = result["emotion"]

    passed, _ = filter_response(reply, text)
    learned   = False

    if passed and reply not in FALLBACKS:
        save_to_dataset(text.lower(), reply)
        learned = True

    turn_number += 1
    save_turn(
        session_id = current_session,
        turn       = turn_number,
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
        "new_facts":   new_facts,
        "score":       result["score"],
    }


# ══════════════════════════════════════════════════════════════════════════════
# STUBS  (keep web_ui.py happy – no-ops since Ollama handles generation)
# ══════════════════════════════════════════════════════════════════════════════

def save_checkpoint():
    """No-op: Qwen weights are managed by Ollama, not saved here."""
    pass


def online_update(user_text: str, reply_text: str, approved: bool):
    """No-op: fine-tuning is handled offline via Ollama model management."""
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
            facts = get_all_facts()
            print(f"Phoenix: Known facts: {facts}")
            continue

        if text.lower() == "/stats":
            stats = memory_stats()
            facts = get_all_facts()
            print(f"Phoenix: {stats}")
            print(f"  Known facts: {facts}")
            continue

        result = chat_step(text)
        emoji  = {"sad": "🤗", "angry": "😌", "anxious": "😊",
                  "happy": "😄", "confused": "🤔"}.get(result["emotion"], "")
        print(f"Phoenix {emoji}: {result['reply']}")
        if result["new_facts"]:
            print(f"   Learned about you: {result['new_facts']}")
