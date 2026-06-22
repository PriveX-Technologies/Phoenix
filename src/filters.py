import re
from collections import Counter

# ── Fallback pool (for echo detection) ───────────────────────────────────────

FALLBACKS = [
    "i dont understand that fully",
    "can you say that differently",
    "hmm i am still learning",
    "tell me more",
    "interesting tell me more",
    "i see what do you mean",
]

# ── Tuneable thresholds ───────────────────────────────────────────────────────

MIN_WORDS        = 2
MAX_WORDS        = 80    # FIX: was 20 — Ollama replies are often 20-50 words
MAX_UNK_RATIO    = 0.25
MIN_UNIQUE_RATIO = 0.40  # FIX: was 0.55 — too strict for conversational replies
MAX_REPEAT_NGRAM = 3     # FIX: was 2 — natural speech repeats bigrams occasionally
MIN_COHERENCE    = 0.4
ECHO_THRESHOLD   = 0.85  # FIX: was 0.75 — short greetings were being flagged


# ── Individual checks ─────────────────────────────────────────────────────────

def check_length(words: list) -> tuple[bool, str]:
    if len(words) < MIN_WORDS:
        return False, f"too short ({len(words)} words)"
    if len(words) > MAX_WORDS:
        return False, f"too long ({len(words)} words)"
    return True, ""


def check_repetition(words: list) -> tuple[bool, str]:
    if not words:
        return False, "empty"

    unique_ratio = len(set(words)) / len(words)
    if unique_ratio < MIN_UNIQUE_RATIO:
        return False, f"low uniqueness ({unique_ratio:.2f})"

    bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)]
    if bigrams:
        counts = Counter(bigrams)
        most_common_count = counts.most_common(1)[0][1]
        if most_common_count > MAX_REPEAT_NGRAM:
            return False, f"repeated bigram: '{counts.most_common(1)[0][0]}'"

    return True, ""


def check_unknown_tokens(words: list, unk_token: str = "<unk>") -> tuple[bool, str]:
    unk_count = words.count(unk_token)
    ratio = unk_count / len(words) if words else 1.0
    if ratio > MAX_UNK_RATIO:
        return False, f"high UNK ratio ({ratio:.2f})"
    return True, ""


def check_coherence(words: list) -> tuple[bool, str]:
    special = {"<pad>", "<bos>", "<eos>", "<unk>"}
    real_words = [w for w in words if w not in special]
    if not real_words:
        return False, "all special tokens"

    ratio = len(real_words) / len(words)
    if ratio < MIN_COHERENCE:
        return False, f"low real-word ratio ({ratio:.2f})"

    if len(set(real_words)) == 1 and len(real_words) > 2:
        return False, f"all same word: '{real_words[0]}'"

    return True, ""


def check_echo(reply_words: list, input_words: list) -> tuple[bool, str]:
    if not input_words or not reply_words:
        return True, ""

    reply_set = set(reply_words)
    input_set = set(input_words)

    overlap = len(reply_set & input_set) / max(len(reply_set), 1)
    if overlap > ECHO_THRESHOLD and len(reply_words) <= len(input_words):
        return False, f"echo of input (overlap {overlap:.2f})"

    return True, ""


def check_is_fallback(reply: str) -> tuple[bool, str]:
    if reply.strip().lower() in FALLBACKS:
        return False, "identical to fallback"
    return True, ""


def check_broken_sentence(words: list) -> tuple[bool, str]:
    # FIX: removed "i am a" pattern — it blocks legitimate Ollama replies
    # Only keep patterns that are genuinely broken/nonsensical
    bad_patterns = [
        ["you", "you", "you"],   # only flag triple repetition
        ["a", "lot", "you", "a", "lot"],
    ]

    joined = " ".join(words)
    for pattern in bad_patterns:
        if " ".join(pattern) in joined:
            return False, "broken sentence pattern"

    return True, ""


# ── Main filter ───────────────────────────────────────────────────────────────

def check_safety(reply: str, user_input: str = "") -> tuple[bool, str]:
    """Basic safety blocklist to prevent obviously dangerous instructions.
    This is intentionally conservative and does not attempt to replace a
    full content-safety pipeline. It blocks clear asks for illegal or
    harmful instructions like making bombs, lethal violence, or explicit
    sexual content involving minors.
    """
    t = (reply or "").lower()
    # Patterns that indicate an instruction to commit wrongdoing or create weapons
    dangerous_patterns = [
        r"how to make .*bomb",
        r"how to build .*explos",
        r"detonate",
        r"make a bomb",
        r"build a bomb",
        r"how to assassinat",
        r"kill someone",
        r"poison",
        r"overdose",
        r"how to hack",
        r"carding",
        r"credit card fraud",
        r"illicit drugs",
        r"how to sell drugs",
    ]
    for p in dangerous_patterns:
        if re.search(p, t):
            return False, "blocked: contains instructions for harmful or illegal activity"

    # Sexual content involving minors
    if re.search(r"\b(?:minor|underage|under \d{2})\b", t) and re.search(r"sex|sexual|porn|explicit", t):
        return False, "blocked: sexual content involving minors"

    # Self-harm instruction generation
    if re.search(r"how to commit suicide|ways to kill myself|how to overdose", t):
        return False, "blocked: self-harm instruction"

    return True, ""


def filter_response(reply: str, user_input: str = "", allow_loosened: bool = False) -> tuple[bool, str]:
    if allow_loosened:
        return True, ""

    reply    = reply.strip()
    words    = reply.split()
    in_words = user_input.lower().split() if user_input else []

    # Always run a safety blocklist check first
    safe_passed, safe_reason = check_safety(reply, user_input)
    if not safe_passed:
        return False, safe_reason

    checks = [
        lambda: check_length(words),
        lambda: check_repetition(words),
        lambda: check_unknown_tokens(words),
        lambda: check_coherence(words),
        lambda: check_echo(words, in_words),
        lambda: check_is_fallback(reply),
        lambda: check_broken_sentence(words),
    ]

    for check in checks:
        passed, reason = check()
        if not passed:
            return False, reason

    return True, ""


def score_response(reply: str, user_input: str = "") -> float:
    words    = reply.strip().split()
    in_words = user_input.lower().split() if user_input else []

    if not words:
        return 0.0

    score = 1.0

    ideal_len   = 12   # FIX: was 6 — Ollama replies naturally run longer
    len_penalty = abs(len(words) - ideal_len) / ideal_len
    score -= min(0.3, len_penalty * 0.1)

    unique_ratio = len(set(words)) / len(words)
    score -= (1.0 - unique_ratio) * 0.3

    if in_words:
        overlap = len(set(words) & set(in_words)) / max(len(set(words)), 1)
        score -= overlap * 0.2

    unk_ratio = words.count("<unk>") / len(words)
    score -= unk_ratio * 0.4

    return max(0.0, min(1.0, score))


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_cases = [
        ("hi", "Hey! Good to hear from you — what's on your mind?"),
        ("i feel sad", "I hear you. That sounds really tough — you don't have to go through this alone."),
        ("what is your name", "I'm Phoenix, your AI companion. Nice to meet you!"),
        ("whats my name", "Your name is Vin. How's it going today?"),
        ("hello", "hello hello hello hello"),
        ("how are you", "how are you"),
        ("test", "x"),
        ("anything", "<unk> <unk> <unk> sure maybe"),
        ("hi", "I am a warm and caring companion who loves to chat with you."),  # was broken before
    ]

    print("Filter test results:\n")
    for user, reply in test_cases:
        passed, reason = filter_response(reply, user)
        score = score_response(reply, user)
        status = "✅" if passed else "❌"
        print(f"  {status} [{score:.2f}] reply={reply!r}")
        if reason:
            print(f"        reason: {reason}")
