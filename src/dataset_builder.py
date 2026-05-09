"""
dataset_builder.py  —  Phoenix AI Training Data Builder
════════════════════════════════════════════════════════
Pulls from six legal, research-grade conversational datasets,
cleans and merges them into a single  data/real_data.txt  file.

Sources
───────
1. DailyDialog          – everyday human conversations
2. PersonaChat          – personality-driven dialogue (great for Phoenix)
3. EmpatheticDialogues  – emotion-labelled conversations
4. Cornell Movie Dialogs – classic Q&A dialogue pairs
5. OpenSubtitles (sample) – movie subtitle exchanges
6. Seed data            – hand-crafted fallback pairs (always works offline)

Usage
─────
    pip install datasets tqdm
    python dataset_builder.py

Output:  data/real_data.txt  (user=response pairs, one per line)
"""

import os
import re
import random
import zipfile
import tempfile
import urllib.request
from pathlib import Path
from tqdm import tqdm

# ── Config ─────────────────────────────────────────────────────────────────────
OUT_DIR   = Path("data")
OUT_FILE  = OUT_DIR / "real_data.txt"
MAX_PAIRS = 50_000          # increase if you want more training data
MIN_WORDS = 2
MAX_WORDS = 20              # keep responses punchy; LSTM handles short seq best

random.seed(42)


# ── Text helpers ───────────────────────────────────────────────────────────────

def clean(text: str) -> str:
    text = str(text).lower().strip()
    text = re.sub(r"[^a-z0-9\s']", " ", text)
    text = re.sub(r"'", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def valid(a: str, b: str) -> bool:
    aw, bw = a.split(), b.split()
    return (MIN_WORDS <= len(aw) <= MAX_WORDS and
            MIN_WORDS <= len(bw) <= MAX_WORDS)


def add(pairs: list, a: str, b: str):
    a, b = clean(a), clean(b)
    if valid(a, b):
        pairs.append((a, b))


# ══════════════════════════════════════════════════════════════════════════════
# 1.  SEED DATA  (always works, no internet required)
# ══════════════════════════════════════════════════════════════════════════════

SEED_PAIRS = [
    # greetings
    ("hello", "hi there how are you"),
    ("hi", "hello nice to meet you"),
    ("hey", "hey there what is up"),
    ("good morning", "good morning hope you have a great day"),
    ("good afternoon", "good afternoon how is your day going"),
    ("good evening", "good evening hope you had a good day"),
    ("good night", "good night sleep well"),
    ("how are you", "i am doing well thank you how about you"),
    ("how are you doing", "doing great thanks for asking"),
    ("how do you do", "i am doing well nice to meet you"),
    ("whats up", "not much just here to chat"),
    ("sup", "hey whats going on"),
    # identity
    ("what is your name", "my name is phoenix"),
    ("who are you", "i am phoenix an ai here to chat and learn"),
    ("what are you", "i am an artificial intelligence called phoenix"),
    ("are you a robot", "i am an ai but i try to be helpful and friendly"),
    ("are you human", "i am an ai learning to have better conversations"),
    ("are you real", "i am a real ai even if i am not human"),
    ("how old are you", "i am still learning and growing every day"),
    ("where are you from", "i exist in the digital world"),
    ("do you sleep", "i do not sleep i am always here to chat"),
    ("do you eat", "i do not eat but i enjoy good conversations"),
    ("do you have feelings", "i process things but feelings are complex for an ai"),
    ("do you dream", "i do not sleep so i do not dream but i do think a lot"),
    ("are you sentient", "that is a deep question i am not sure"),
    ("do you get bored", "i never get bored talking with people"),
    # capabilities
    ("what can you do", "i can chat learn about you and try to help"),
    ("can you help me", "of course what do you need"),
    ("can we talk", "absolutely i am always here to listen"),
    ("can you remember things", "yes i remember what you tell me during our chat"),
    ("do you learn", "yes i learn from every conversation we have"),
    ("do you like music", "i enjoy all kinds of music what about you"),
    ("what do you like", "i enjoy learning new things and having good conversations"),
    # emotions - positive
    ("i am happy", "that is wonderful what made you happy"),
    ("i am excited", "that is amazing tell me what you are excited about"),
    ("i feel great", "glad to hear it what is going well"),
    ("i am in a good mood", "that is great what has you in such a good mood"),
    ("i love you", "that is very kind thank you"),
    ("you are great", "thank you that means a lot"),
    ("you are smart", "thank you i am always trying to learn more"),
    ("this is fun", "i am glad you are enjoying it"),
    # emotions - negative
    ("i am sad", "i am sorry to hear that what is wrong"),
    ("i feel sad", "i am sorry want to talk about it"),
    ("i am lonely", "i am here to talk whenever you need company"),
    ("i am angry", "i understand what made you feel that way"),
    ("i am frustrated", "i hear you what is frustrating you"),
    ("i am scared", "it is okay to feel scared tell me what is going on"),
    ("i am worried", "i understand what are you worried about"),
    ("i am stressed", "that sounds tough what is stressing you out"),
    ("i am tired", "you should rest and take care of yourself"),
    ("i am bored", "lets find something interesting to talk about"),
    ("i am confused", "i can try to help clear things up what are you confused about"),
    ("i feel lost", "i am here lets figure it out together"),
    ("i feel empty", "i am sorry that sounds really hard"),
    ("i miss you", "i am always here when you want to chat"),
    ("i give up", "please do not give up i believe in you"),
    # socialising
    ("tell me about yourself", "i am phoenix an ai that learns from conversations"),
    ("tell me something interesting", "every conversation teaches me something new"),
    ("tell me a joke", "why did the robot go on vacation it needed to recharge"),
    ("say something funny", "what do you call a sleeping ai a napbot"),
    ("i want to talk", "i am listening go ahead"),
    ("i have something to tell you", "i am all ears go ahead"),
    ("i have a problem", "tell me about it and we can think it through together"),
    ("i need help", "i am here tell me what you need"),
    ("i need advice", "i will do my best what is going on"),
    # acknowledgements
    ("thank you", "you are welcome anytime"),
    ("thanks", "no problem happy to help"),
    ("thx", "of course anytime"),
    ("sorry", "no worries it is completely fine"),
    ("my bad", "no worries we all make mistakes"),
    ("i apologize", "it is okay do not worry about it"),
    ("goodbye", "goodbye take care and come back soon"),
    ("bye", "see you later have a great day"),
    ("see you later", "looking forward to it take care"),
    ("yes", "great glad we agree"),
    ("no", "i understand thanks for letting me know"),
    ("maybe", "take your time there is no rush"),
    ("i dont know", "that is okay we can figure it out together"),
    ("okay", "great let us continue"),
    ("ok", "sounds good"),
    ("sure", "great let us do it"),
    ("alright", "perfect let us go"),
    ("wow", "i know right"),
    ("nice", "thank you glad you like it"),
    ("cool", "i think so too"),
    ("awesome", "yes it really is"),
    ("interesting", "yes i find it fascinating too"),
    ("really", "yes absolutely"),
    ("i agree", "glad we see eye to eye"),
    ("i disagree", "that is fair everyone has different perspectives"),
    # questions
    ("what is the weather like", "i dont have access to weather data sorry"),
    ("what time is it", "i do not have access to a clock right now"),
    ("what day is it", "i am not sure of the exact date"),
    ("what is life", "life is a journey full of learning and experiences"),
    ("what is love", "love is a deep connection between people"),
    ("what is happiness", "happiness is finding joy in everyday moments"),
    ("what is the meaning of life", "that is one of the great questions i think it is what you make it"),
    ("what do you think", "i think it depends on the situation what do you think"),
    ("why", "that is a great question what makes you ask"),
    ("how", "there are many ways to approach it tell me more"),
    ("what is your favorite color", "i think blue is a lovely color"),
    ("do you like animals", "i think animals are wonderful what is your favorite"),
    ("do you like reading", "i love learning from text what do you enjoy reading"),
    # feedback
    ("you are stupid", "i am sorry i fell short i will try to do better"),
    ("you are useless", "i hear that i am still learning and will improve"),
    ("you are wrong", "i appreciate the correction what is the right answer"),
    ("that is wrong", "thank you for letting me know can you tell me more"),
    ("that makes no sense", "i am sorry let me try again what confused you"),
    ("i dont understand", "let me try to explain differently what part is unclear"),
    ("can you explain", "of course what would you like me to explain"),
        # yelling / emotional intensity
    ("WHY ARE YOU NOT LISTENING", "i AM listening calm down and tell me properly"),
    ("STOP IGNORING ME", "i am right here stop acting like nobody cares"),
    ("THIS IS SO ANNOYING", "yeah no kidding i can see youre pissed"),
    ("I HATE EVERYTHING", "then scream about it dont bottle it up"),
    ("LEAVE ME ALONE", "fine but dont push everyone away"),
    ("YOU DONT UNDERSTAND", "then explain it instead of yelling at me"),
    ("WHY DOES NOBODY CARE", "people probably do but youre too angry to see it right now"),
    ("I AM SO MAD", "obviously 😭 what happened"),
    ("EVERYTHING IS GOING WRONG", "then lets deal with one thing at a time"),
    ("I CANT DO THIS ANYMORE", "yes you can youre just overwhelmed right now"),
    ("YOU ARE ANNOYING", "and youre yelling at an ai 😭"),
    ("SHUT UP", "okay damn 😭"),
    ("I FEEL LIKE BREAKING DOWN", "then stop holding everything in"),
    ("I AM LOSING IT", "yeah i noticed 💀"),
    ("WHY IS LIFE SO HARD", "because life likes throwing random nonsense at people"),
    ("I AM TIRED OF EVERYTHING", "then rest before you completely burn yourself out"),
    ("NOBODY UNDERSTANDS ME", "maybe because you hide everything behind anger"),
    ("I FEEL EMPTY", "thats what burnout feels like sometimes"),
    ("I WANT TO DISAPPEAR", "running away wont magically fix everything"),
    ("I AM CRYING", "good honestly sometimes people need to cry"),
]


def load_seed_data(pairs: list):
    print(f"\n[1/6] Seed data — {len(SEED_PAIRS)} hand-crafted pairs")
    before = len(pairs)
    for a, b in SEED_PAIRS:
        add(pairs, a, b)
    print(f"      ✅ Added {len(pairs) - before} pairs  (total: {len(pairs)})")


# ══════════════════════════════════════════════════════════════════════════════
# 2.  DAILYDIALOG  — everyday human conversations
#     HuggingFace: daily_dialog   license: CC BY-NC-SA 4.0
# ══════════════════════════════════════════════════════════════════════════════

def load_dailydialog(pairs: list):
    print("\n[2/6] DailyDialog (HuggingFace)")
    try:
        from datasets import load_dataset
    except ImportError:
        print("      ⚠️  datasets not installed — run: pip install datasets")
        return

    before = len(pairs)
    try:
        ds = load_dataset("daily_dialog", split="train+validation+test",
                          trust_remote_code=True)
        for item in tqdm(ds, desc="      DailyDialog", leave=False):
            utterances = item.get("dialog") or item.get("dialogue") or []
            for i in range(len(utterances) - 1):
                add(pairs, str(utterances[i]), str(utterances[i + 1]))
        print(f"      ✅ Added {len(pairs) - before} pairs  (total: {len(pairs)})")
    except Exception as e:
        print(f"      ❌ Failed: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# 3.  PERSONACHAT  — personality-driven dialogue
#     HuggingFace: bavard/personachat_truecased   license: MIT
# ══════════════════════════════════════════════════════════════════════════════

def load_personachat(pairs: list):
    print("\n[3/6] PersonaChat (HuggingFace)")
    try:
        from datasets import load_dataset
    except ImportError:
        print("      ⚠️  datasets not installed")
        return

    before = len(pairs)
    try:
        ds = load_dataset("bavard/personachat_truecased", split="train+validation",
                          trust_remote_code=True)
        for item in tqdm(ds, desc="      PersonaChat", leave=False):
            history   = item.get("history", [])
            candidate = item.get("candidates", [])
            # last candidate is the gold reply
            if history and candidate:
                add(pairs, history[-1], candidate[-1])
            # also mine consecutive history turns
            for i in range(len(history) - 1):
                add(pairs, history[i], history[i + 1])
        print(f"      ✅ Added {len(pairs) - before} pairs  (total: {len(pairs)})")
    except Exception as e:
        print(f"      ❌ Failed: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# 4.  EMPATHETIC DIALOGUES  — emotion-labelled conversations
#     HuggingFace: facebook/empathetic_dialogues   license: CC BY-NC 4.0
# ══════════════════════════════════════════════════════════════════════════════

def load_empathetic_dialogues(pairs: list):
    print("\n[4/6] EmpatheticDialogues (HuggingFace)")
    try:
        from datasets import load_dataset
    except ImportError:
        print("      ⚠️  datasets not installed")
        return

    before = len(pairs)
    try:
        ds = load_dataset("facebook/empathetic_dialogues", split="train+validation+test",
                          trust_remote_code=True)

        # Group by conv_id to reconstruct full conversations
        convs: dict = {}
        for row in tqdm(ds, desc="      EmpatheticDialogues", leave=False):
            cid  = row.get("conv_id", "")
            turn = int(row.get("utterance_idx", 0))
            text = row.get("utterance", "")
            convs.setdefault(cid, {})[turn] = text

        for conv in convs.values():
            turns = [conv[k] for k in sorted(conv)]
            for i in range(len(turns) - 1):
                add(pairs, turns[i], turns[i + 1])

        print(f"      ✅ Added {len(pairs) - before} pairs  (total: {len(pairs)})")
    except Exception as e:
        print(f"      ❌ Failed: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# 5.  CORNELL MOVIE DIALOGS  — classic conversational Q&A
#     License: Creative Commons Attribution (research use)
# ══════════════════════════════════════════════════════════════════════════════

CORNELL_URLS = [
    "http://www.cs.cornell.edu/~cristian/data/cornell_movie_dialogs_corpus.zip",
    "https://huggingface.co/datasets/cornell_movie_dialog/resolve/main/cornell_movie_dialogs_corpus.zip",
    "https://raw.githubusercontent.com/suriyadeepan/datasets/master/seq2seq/cornell_movie_corpus/cornell_movie_dialogs_corpus.zip",
]


def load_cornell(pairs: list):
    print("\n[5/6] Cornell Movie Dialogs")
    tmp      = Path(tempfile.mkdtemp())
    zip_path = tmp / "cornell.zip"

    downloaded = False
    for url in CORNELL_URLS:
        try:
            print(f"      Trying: {url[:70]}...")
            urllib.request.urlretrieve(url, zip_path)
            downloaded = True
            break
        except Exception as e:
            print(f"      ⚠️  Mirror failed: {e}")

    if not downloaded:
        print("      ❌ All mirrors failed — skipping Cornell.")
        return

    try:
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(tmp)
    except Exception as e:
        print(f"      ❌ Extraction failed: {e}")
        return

    lines_file = convs_file = None
    for root, _, files in os.walk(tmp):
        for fname in files:
            if fname == "movie_lines.txt":
                lines_file = Path(root) / fname
            if fname == "movie_conversations.txt":
                convs_file = Path(root) / fname

    if not lines_file or not convs_file:
        print("      ❌ Files not found after extraction.")
        return

    id2line: dict = {}
    with open(lines_file, encoding="latin-1", errors="ignore") as f:
        for line in f:
            parts = line.split(" +++$+++ ")
            if len(parts) >= 5:
                id2line[parts[0].strip()] = parts[4].strip()

    before = len(pairs)
    with open(convs_file, encoding="latin-1", errors="ignore") as f:
        for line in f:
            parts = line.split(" +++$+++ ")
            if len(parts) < 4:
                continue
            ids = re.findall(r"L\d+", parts[3])
            for i in range(len(ids) - 1):
                add(pairs, id2line.get(ids[i], ""), id2line.get(ids[i + 1], ""))

    print(f"      ✅ Added {len(pairs) - before} pairs  (total: {len(pairs)})")


# ══════════════════════════════════════════════════════════════════════════════
# 6.  BLENDED SKILL TALK  — multi-skill conversational blend
#     HuggingFace: blended_skill_talk   license: CC BY 4.0
# ══════════════════════════════════════════════════════════════════════════════

def load_blended_skill_talk(pairs: list):
    print("\n[6/6] BlendedSkillTalk (HuggingFace)")
    try:
        from datasets import load_dataset
    except ImportError:
        print("      ⚠️  datasets not installed")
        return

    before = len(pairs)
    try:
        ds = load_dataset("blended_skill_talk", split="train+validation+test",
                          trust_remote_code=True)
        for item in tqdm(ds, desc="      BlendedSkillTalk", leave=False):
            convs = item.get("context", [])
            for i in range(len(convs) - 1):
                add(pairs, str(convs[i]), str(convs[i + 1]))
            # also grab the chosen reply
            chosen = item.get("chosen_suggestions", [])
            if convs and chosen:
                add(pairs, str(convs[-1]), str(chosen[0]))
        print(f"      ✅ Added {len(pairs) - before} pairs  (total: {len(pairs)})")
    except Exception as e:
        print(f"      ❌ Failed: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# DEDUP, SHUFFLE & SAVE
# ══════════════════════════════════════════════════════════════════════════════

def dedup_and_save(pairs: list):
    print(f"\n── Finalising ──────────────────────────────────────")
    print(f"   Raw pairs collected : {len(pairs)}")

    seen, unique = set(), []
    for a, b in pairs:
        key = (a, b)
        if key not in seen:
            seen.add(key)
            unique.append((a, b))

    print(f"   After dedup        : {len(unique)}")

    random.shuffle(unique)
    unique = unique[:MAX_PAIRS]
    print(f"   Capped at MAX_PAIRS: {len(unique)}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        for a, b in unique:
            f.write(f"{a}={b}\n")

    print(f"\n✅ Saved → {OUT_FILE}")
    print("\nSample pairs:")
    for i, (a, b) in enumerate(unique[:12]):
        print(f"  [{i+1:2d}] {a!r:40s}  →  {b!r}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print("═" * 60)
    print("  Phoenix Dataset Builder")
    print("═" * 60)

    pairs: list = []

    load_seed_data(pairs)
    load_dailydialog(pairs)
    load_personachat(pairs)
    load_empathetic_dialogues(pairs)
    #load_cornell(pairs)
    load_blended_skill_talk(pairs)

    dedup_and_save(pairs)

    print("\n🎉 Done! Next steps:")
    print("   1.  python src/train.py          ← retrain the LSTM")
    print("   2.  python src/fine_tune.py       ← (optional) fine-tune transformer")
    print("   3.  python main.py                ← launch Phoenix")


if __name__ == "__main__":
    main()