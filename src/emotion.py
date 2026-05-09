import re

# ── Emotion lexicons ──────────────────────────────────────────────────────────

EMOTION_PATTERNS = {
    "sad": [
        r"\b(sad|unhappy|depressed|miserable|crying|cry|tears|hopeless|lonely|alone|hurt|heartbroken|down|gloomy)\b",
        r"\b(i feel (bad|terrible|awful|horrible|empty|lost))\b",
        r"\b(everything is wrong|nothing matters|i give up)\b",
    ],
    "angry": [
        r"\b(angry|furious|rage|hate|annoyed|irritated|frustrated|mad|livid|pissed|upset)\b",
        r"\b(i (hate|can't stand|despise))\b",
        r"\b(this is (stupid|ridiculous|terrible|awful|garbage|trash))\b",
    ],
    "anxious": [
        r"\b(anxious|worried|nervous|scared|afraid|fear|panic|stress|overwhelmed|anxiousness|anxiety)\b",
        r"\b(i (don't know what to do|can't handle|am worried|am scared))\b",
        r"\b(what if|i'm not sure|i'm afraid)\b",
    ],
    "happy": [
        r"\b(happy|great|awesome|fantastic|excited|wonderful|amazing|love|joy|glad|thrilled|delighted)\b",
        r"\b(i (feel good|am happy|am excited|am glad|love this))\b",
        r"\b(this is (great|amazing|awesome|wonderful|fantastic))\b",
    ],
    "confused": [
        r"\b(confused|don't understand|what do you mean|unclear|lost|huh|idk|no idea)\b",
        r"\b(i (don't get it|am confused|can't figure out|don't know))\b",
        r"\b(what does .* mean|how does .* work)\b",
    ],
    "neutral": [],
}

# ── Temperature map ───────────────────────────────────────────────────────────
# Lower temp = more focused/careful; Higher = more creative/warm

EMOTION_TEMPERATURE = {
    "sad":      0.2,   # careful, gentle
    "angry":    0.2,   # calm, measured
    "anxious":  0.25,  # reassuring, steady
    "happy":    0.45,  # enthusiastic, playful
    "confused": 0.3,   # clear, structured
    "neutral":  0.10,  # balanced
}

# ── Response tone hints (prepended context for generation) ────────────────────

EMOTION_TONE = {
    "sad":      "respond with empathy and warmth",
    "angry":    "respond calmly and acknowledge their frustration",
    "anxious":  "respond with reassurance and clarity",
    "happy":    "respond with energy and positivity",
    "confused": "respond clearly and helpfully",
    "neutral":  "",
}


def detect_emotion(text: str) -> str:
    text_lower = text.lower()
    scores = {emotion: 0 for emotion in EMOTION_PATTERNS}

    for emotion, patterns in EMOTION_PATTERNS.items():
        if emotion == "neutral":
            continue
        for pattern in patterns:
            if re.search(pattern, text_lower):
                scores[emotion] += 1

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "neutral"


def get_temperature(emotion: str) -> float:
    """Returns the generation temperature for a given emotion."""
    return EMOTION_TEMPERATURE.get(emotion, 0.35)


def get_tone_hint(emotion: str) -> str:
    """Returns a tone hint string to prepend to context."""
    return EMOTION_TONE.get(emotion, "")


def emotion_summary(text: str) -> dict:
    """Returns a full emotion analysis dict."""
    emotion = detect_emotion(text)
    return {
        "emotion":     emotion,
        "temperature": get_temperature(emotion),
        "tone_hint":   get_tone_hint(emotion),
    }


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    tests = [
        "I feel so sad and lonely today",
        "This is absolutely amazing I love it!",
        "I'm so frustrated and angry right now",
        "I don't understand what you mean",
        "I'm really stressed and worried about everything",
        "What is the weather like",
    ]
    for t in tests:
        result = emotion_summary(t)
        print(f"  {t!r}")
        print(f"    → emotion={result['emotion']}, temp={result['temperature']}, tone={result['tone_hint']!r}\n")