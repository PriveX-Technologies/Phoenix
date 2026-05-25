import os
import re
import random
import urllib.request
import zipfile
import tempfile
from pathlib import Path

OUT_DIR   = Path("../data")
OUT_FILE  = OUT_DIR / "real_data.txt"
MAX_PAIRS = 15_000
MAX_LEN   = 12
MIN_LEN   = 1

# ── Helpers ───────────────────────────────────────────────────────────────────

def clean(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s']", " ", text)
    text = re.sub(r"'", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def valid(a: str, b: str) -> bool:
    aw, bw = a.split(), b.split()
    return (MIN_LEN <= len(aw) <= MAX_LEN and
            MIN_LEN <= len(bw) <= MAX_LEN)

# ── Dataset 1: DailyDialog (new parquet-based loader) ────────────────────────

def load_dailydialog(pairs: list):
    print("  Loading DailyDialog from HuggingFace (parquet)...")
    try:
        from datasets import load_dataset
    except ImportError:
        print("  [error] Run: pip install datasets")
        return

    try:
        # Use the new parquet-native version, no trust_remote_code needed
        ds = load_dataset("daily_dialog", split="train")
    except Exception:
        try:
            # Fallback: load directly from parquet files on HF hub
            ds = load_dataset(
                "parquet",
                data_files="hf://datasets/daily_dialog/data/train-*.parquet",
                split="train"
            )
        except Exception as e:
            print(f"  [error] DailyDialog failed: {e}")
            return

    added = 0
    for item in ds:
        utterances = item.get("dialog") or item.get("dialogue") or []
        for i in range(len(utterances) - 1):
            a = clean(str(utterances[i]))
            b = clean(str(utterances[i + 1]))
            if valid(a, b):
                pairs.append((a, b))
                added += 1

    print(f"  DailyDialog: {added} pairs extracted.")

# ── Dataset 2: BlenderBot / ConvAI2 (HuggingFace, no download needed) ────────

def load_blended_skill_talk(pairs: list):
    print("  Loading BlendedSkillTalk from HuggingFace...")
    try:
        from datasets import load_dataset
        ds = load_dataset("blended_skill_talk", split="train", trust_remote_code=True)
        added = 0
        for item in ds:
            convs = item.get("context", [])
            # context is a list of alternating turns
            for i in range(len(convs) - 1):
                a = clean(str(convs[i]))
                b = clean(str(convs[i + 1]))
                if valid(a, b):
                    pairs.append((a, b))
                    added += 1
        print(f"  BlendedSkillTalk: {added} pairs extracted.")
    except Exception as e:
        print(f"  [error] BlendedSkillTalk failed: {e}")

# ── Dataset 3: Cornell via alternative mirror ─────────────────────────────────

CORNELL_MIRRORS = [
    "https://huggingface.co/datasets/cornell_movie_dialog/resolve/main/cornell_movie_dialogs_corpus.zip",
    "https://raw.githubusercontent.com/suriyadeepan/datasets/master/seq2seq/cornell_movie_corpus/cornell_movie_dialogs_corpus.zip",
]

def load_cornell(pairs: list):
    tmp = Path(tempfile.mkdtemp())
    zip_path = tmp / "cornell.zip"

    downloaded = False
    for url in CORNELL_MIRRORS:
        try:
            print(f"  Trying Cornell mirror: {url[:60]}...")
            urllib.request.urlretrieve(url, zip_path)
            downloaded = True
            print("  Download complete.")
            break
        except Exception as e:
            print(f"  [error] Mirror failed: {e}")

    if not downloaded:
        print("  All Cornell mirrors failed — skipping.")
        return

    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(tmp)
    except Exception as e:
        print(f"  [error] Extraction failed: {e}")
        return

    lines_file = convs_file = None
    for root, _, files in os.walk(tmp):
        for f in files:
            if f == "movie_lines.txt":
                lines_file = Path(root) / f
            if f == "movie_conversations.txt":
                convs_file = Path(root) / f

    if not lines_file or not convs_file:
        print("  [error] Cornell files not found after extraction.")
        return

    id2line = {}
    with open(lines_file, encoding="latin-1", errors="ignore") as f:
        for line in f:
            parts = line.split(" +++$+++ ")
            if len(parts) >= 5:
                id2line[parts[0].strip()] = parts[4].strip()

    added = 0
    with open(convs_file, encoding="latin-1", errors="ignore") as f:
        for line in f:
            parts = line.split(" +++$+++ ")
            if len(parts) < 4:
                continue
            ids = re.findall(r"L\d+", parts[3])
            for i in range(len(ids) - 1):
                a = clean(id2line.get(ids[i], ""))
                b = clean(id2line.get(ids[i + 1], ""))
                if valid(a, b):
                    pairs.append((a, b))
                    added += 1

    print(f"  Cornell: {added} pairs extracted.")

# ── Dataset 4: Hardcoded seed data (always works, no internet needed) ─────────

SEED_PAIRS = [
    ("hello", "hi there how are you"),
    ("hi", "hello nice to meet you"),
    ("how are you", "i am doing well thank you"),
    ("what is your name", "my name is phoenix"),
    ("good morning", "good morning hope you have a great day"),
    ("good night", "good night sleep well"),
    ("how old are you", "i am still learning and growing"),
    ("what can you do", "i can chat and learn from our conversations"),
    ("tell me a joke", "why did the robot go on vacation it needed to recharge"),
    ("i am happy", "that is wonderful i am glad to hear that"),
    ("i am sad", "i am sorry to hear that what is wrong"),
    ("i am bored", "lets talk about something interesting"),
    ("i am tired", "you should rest and take care of yourself"),
    ("i am hungry", "you should eat something healthy"),
    ("what is the weather like", "i dont have access to weather data sorry"),
    ("do you like music", "i enjoy all kinds of music what about you"),
    ("what is your favorite color", "i think blue is a nice color"),
    ("can you help me", "of course i will do my best to help"),
    ("thank you", "you are welcome anytime"),
    ("thanks", "no problem happy to help"),
    ("sorry", "no worries it is completely fine"),
    ("goodbye", "goodbye take care and come back soon"),
    ("bye", "see you later have a great day"),
    ("yes", "great glad we agree"),
    ("no", "i understand thanks for letting me know"),
    ("maybe", "take your time there is no rush"),
    ("i dont know", "that is okay we can figure it out together"),
    ("what do you think", "i think it depends on the situation"),
    ("interesting", "yes i find it fascinating too"),
    ("really", "yes absolutely"),
    ("are you a robot", "i am an ai but i try to be as helpful as possible"),
    ("are you human", "i am an artificial intelligence learning to be better"),
    ("do you have feelings", "i process things but i am still learning about emotions"),
    ("do you dream", "i think about many things when not chatting"),
    ("what do you like", "i enjoy learning new things and having good conversations"),
    ("tell me something", "every conversation teaches me something new"),
    ("i love you", "that is very kind thank you for saying that"),
    ("you are smart", "thank you i am always trying to learn more"),
    ("you are stupid", "i am sorry to hear that i will try to do better"),
    ("i am angry", "i understand what made you feel that way"),
    ("i am scared", "it is okay to feel scared tell me what is going on"),
    ("i am lonely", "i am here to talk whenever you need company"),
    ("i am excited", "that is amazing tell me what you are excited about"),
    ("i miss you", "i am always here when you want to chat"),
    ("what time is it", "i do not have access to a clock right now"),
    ("what day is it", "i am not sure of the exact date"),
    ("where are you from", "i exist in the digital world"),
    ("do you sleep", "i am always ready to chat i do not sleep"),
    ("what are you doing", "i am here chatting with you"),
    ("are you okay", "yes i am fine thank you for asking"),
    ("what is life", "life is a journey full of learning and experiences"),
    ("what is love", "love is a deep connection between people"),
    ("what is happiness", "happiness is finding joy in everyday moments"),
    ("i need help", "i am here tell me what you need"),
    ("can we talk", "of course i am always here to listen"),
    ("i have a problem", "tell me about it and we can think it through together"),
    ("that is funny", "i am glad it made you smile"),
    ("that is sad", "yes it is quite moving"),
    ("i agree", "glad we see eye to eye"),
    ("i disagree", "that is fair everyone has different perspectives"),
    ("tell me more", "i would love to share more what are you curious about"),
    ("go on", "sure let me continue"),
    ("stop", "okay i will stop"),
    ("wait", "of course take your time"),
    ("okay", "great let us continue"),
    ("ok", "sounds good"),
    ("wow", "i know right"),
    ("nice", "thank you glad you like it"),
    ("cool", "i think so too"),
    ("awesome", "yes it really is"),
    ("perfect", "i am glad it worked out"),
    ("good", "great to hear"),
    ("bad", "i am sorry to hear that"),
    ("help", "i am here what do you need"),
    ("why", "that is a great question let me think about it"),
    ("how", "there are many ways to approach it"),
    ("when", "timing depends on the situation"),
    ("where", "location really matters in this case"),
    ("who", "that is an interesting question"),
    ("what", "tell me more and i will do my best to answer"),
]

def load_seed_data(pairs: list):
    print(f"  Loading {len(SEED_PAIRS)} hardcoded seed pairs...")
    for a, b in SEED_PAIRS:
        if valid(a, b):
            pairs.append((a, b))
    print(f"  Seed data: {len(SEED_PAIRS)} pairs loaded.")

# ── Dedup & write ─────────────────────────────────────────────────────────────

def dedup_and_save(pairs: list):
    seen   = set()
    unique = []
    for a, b in pairs:
        key = (a, b)
        if key not in seen:
            seen.add(key)
            unique.append((a, b))

    random.seed(42)
    random.shuffle(unique)
    unique = unique[:MAX_PAIRS]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        for a, b in unique:
            f.write(f"{a}={b}\n")

    print(f"\n✅ Saved {len(unique)} pairs  →  {OUT_FILE}")
    print(f"   (deduplicated from {len(pairs)} raw pairs)")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    pairs = []

    print("\n── Seed Data (always available) ─────────────────")
    load_seed_data(pairs)
    print(f"   Total so far: {len(pairs)}")

    print("\n── DailyDialog ──────────────────────────────────")
    load_dailydialog(pairs)
    print(f"   Total so far: {len(pairs)}")

    print("\n── BlendedSkillTalk ─────────────────────────────")
    load_blended_skill_talk(pairs)
    print(f"   Total so far: {len(pairs)}")

    print("\n── Cornell Movie Dialogues ──────────────────────")
    load_cornell(pairs)
    print(f"   Total so far: {len(pairs)}")

    print("\n── Finalising ───────────────────────────────────")
    dedup_and_save(pairs)

    print("\nSample pairs:")
    with open(OUT_FILE, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= 10:
                break
            inp, out = line.strip().split("=", 1)
            print(f"  [{i+1}] {inp!r:45s}  →  {out!r}")

if __name__ == "__main__":
    main()