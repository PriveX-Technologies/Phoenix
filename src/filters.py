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
MAX_WORDS        = 20
MAX_UNK_RATIO    = 0.25   # allow up to 25% UNK before rejecting
MIN_UNIQUE_RATIO = 0.55   # unique words / total words
MAX_REPEAT_NGRAM = 2      # reject if any bigram appears more than this many times
MIN_COHERENCE    = 0.4    # ratio of "real" words (non-special)
ECHO_THRESHOLD   = 0.75   # if reply shares >75% words with input → echo


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

    # Word uniqueness ratio
    unique_ratio = len(set(words)) / len(words)
    if unique_ratio < MIN_UNIQUE_RATIO:
        return False, f"low uniqueness ({unique_ratio:.2f})"

    # Bigram repetition
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

    # All identical words
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

    if reply.strip() in FALLBACKS:
        return False, "identical to fallback"
    return True, ""


# ── Main filter ───────────────────────────────────────────────────────────────

def filter_response(reply: str, user_input: str = "") -> tuple[bool, str]:
    reply   = reply.strip()
    words   = reply.split()
    in_words = user_input.lower().split() if user_input else []

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

    # Penalise too short / too long
    ideal_len = 6
    len_penalty = abs(len(words) - ideal_len) / ideal_len
    score -= min(0.3, len_penalty * 0.1)

    # Penalise low uniqueness
    unique_ratio = len(set(words)) / len(words)
    score -= (1.0 - unique_ratio) * 0.3

    # Penalise echo
    if in_words:
        overlap = len(set(words) & set(in_words)) / max(len(set(words)), 1)
        score -= overlap * 0.2

    # Penalise UNK
    unk_ratio = words.count("<unk>") / len(words)
    score -= unk_ratio * 0.4

    return max(0.0, min(1.0, score))



def check_broken_sentence(words: list) -> tuple[bool, str]:
    bad_patterns = [
        ["i", "am", "a"],
        ["you", "you"],
        ["a", "lot", "you"],
    ]

    joined = " ".join(words)

    for pattern in bad_patterns:
        if " ".join(pattern) in joined:
            return False, "broken sentence pattern"

    return True, ""

# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_cases = [
        ("hi", "hello how are you doing today"),
        ("i feel sad", "i am sorry to hear that what happened"),
        ("what is your name", "my name is phoenix nice to meet you"),
        ("hello", "hello hello hello hello"),
        ("how are you", "how are you"),                  # echo
        ("test", "x"),                                   # too short
        ("anything", "<unk> <unk> <unk> sure maybe"),   # high unk
    ]

    print("Filter test results:\n")
    for user, reply in test_cases:
        passed, reason = filter_response(reply, user)
        score = score_response(reply, user)
        status = "✅" if passed else "❌"
        print(f"  {status} [{score:.2f}] reply={reply!r}")
        if reason:
            print(f"        reason: {reason}")