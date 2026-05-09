import torch
import torch.nn as nn
import torch.optim as optim
import random
import os

from model   import PhoenixModel
from dataset import PhoenixDataset
from emotion import emotion_summary
from memory  import (
    new_session, save_turn, build_context_string,
    build_profile_string, extract_and_save_facts,
    get_all_facts, memory_stats, clear_session_memory,
)
from filters import filter_response, score_response

# ── Config ────────────────────────────────────────────────────────────────────
LR_ONLINE        = 5e-5
CLIP             = 0.5
SAVE_EVERY       = 10
DATA_FILE        = "data/real_data.txt"
PHOENIX_PT       = "models/phoenix.pt"
TRANSFORMER_PATH = "models/phoenix_transformer"

# ── Transformer DISABLED — base DialoGPT generates garbage without fine-tuning.
# To re-enable: run fine_tune.py, then uncomment the block below.

try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        if os.path.isdir(TRANSFORMER_PATH):
            ft_tokenizer = AutoTokenizer.from_pretrained(TRANSFORMER_PATH)
            ft_model     = AutoModelForCausalLM.from_pretrained(TRANSFORMER_PATH)
            print("✅ Transformer model loaded.")
except Exception as e:
        print(f"⚠️  Transformer load failed: {e}")

# ── Phoenix LSTM checkpoint ───────────────────────────────────────────────────
model            = None
dataset          = None
online_optimizer = None
criterion        = None
vocab_size       = 0
cfg              = {}

if os.path.isfile(PHOENIX_PT):
    try:
        print(f"Loading Phoenix checkpoint from {PHOENIX_PT}...")
        checkpoint = torch.load(PHOENIX_PT, map_location="cpu")
        cfg        = checkpoint.get("config", {})
        vocab_size = cfg.get("vocab_size", len(checkpoint["vocab"]))

        model = PhoenixModel(
            vocab_size  = vocab_size,
            embed_size  = cfg.get("embed_size", 64),
            hidden_size = cfg.get("hidden_size", 128),
        )
        model.load_state_dict(checkpoint["model"])

        online_optimizer = optim.Adam(model.parameters(), lr=LR_ONLINE)
        criterion        = nn.CrossEntropyLoss(ignore_index=0)

        dataset          = PhoenixDataset()
        dataset.word2idx = checkpoint["vocab"]
        dataset.idx2word = {i: w for w, i in dataset.word2idx.items()}
        dataset.vocab    = list(dataset.word2idx.keys())

        print("✅ Phoenix LSTM loaded.")
    except Exception as e:
        print(f"❌ Phoenix checkpoint load failed: {e}")
        model = None
else:
    print(f"⚠️  Phoenix checkpoint not found at '{PHOENIX_PT}'.")
    print("   Run train.py to create it.")

# ── Sanity check ──────────────────────────────────────────────────────────────
if model is None and ft_model is None:
    print("\n❌ ERROR: No models available. Phoenix cannot respond.")
    print("   Fix: run train.py (LSTM) and/or fine_tune.py (transformer).\n")

# ── Session ───────────────────────────────────────────────────────────────────
current_session = new_session()
turn_number     = 0
approved_count  = 0

# ── Fallbacks ─────────────────────────────────────────────────────────────────
FALLBACKS = [
    "i dont understand that fully",
    "can you say that differently",
    "hmm i am still learning",
    "tell me more",
]


# ── Rule-based fallback responder ────────────────────────────────────────────
# Used when the LSTM output fails filters. Clean, coherent replies guaranteed.

RULE_RESPONSES = [
    # greetings
    (["hi", "hello", "hey", "sup", "yo"],
     ["hey there! how are you doing?", "hello! what's on your mind?", "hi! good to hear from you."]),
    # farewells
    (["bye", "goodbye", "see you", "later", "cya"],
     ["goodbye! take care.", "see you later!", "bye! come back anytime."]),
    # how are you
    (["how are you", "how r u", "how do you feel", "you ok"],
     ["i'm doing well, thanks for asking!", "i'm great! how about you?", "all good here. what's up?"]),
    # name
    (["your name", "who are you", "what are you"],
     ["i'm phoenix, your ai companion.", "my name is phoenix. nice to meet you!", "i'm phoenix — here to chat."]),
    # thanks
    (["thank", "thanks", "thx", "ty"],
     ["you're welcome!", "anytime!", "happy to help."]),
    # sorry / apology
    (["sorry", "my bad", "apolog"],
     ["no worries at all!", "it's totally fine.", "don't worry about it."]),
    # help
    (["help", "assist", "support", "can you"],
     ["of course! what do you need?", "sure, i'll do my best. what's up?", "i'm here to help — go ahead."]),
    # feelings - sad
    (["sad", "unhappy", "depressed", "lonely", "cry", "hurt"],
     ["i'm sorry to hear that. want to talk about it?", "that sounds really tough. i'm here for you.", "i hear you. what's going on?"]),
    # feelings - happy
    (["happy", "great", "awesome", "excited", "amazing"],
     ["that's wonderful! tell me more.", "love to hear that! what's got you excited?", "amazing! i'm glad things are going well."]),
    # feelings - angry
    (["angry", "frustrated", "annoyed", "mad", "furious"],
     ["i get it — that sounds really frustrating.", "let's take a breath. what happened?", "i hear you. what's making you angry?"]),
    # feelings - anxious
    (["anxious", "nervous", "scared", "worried", "stress"],
     ["it's okay to feel that way. i'm here with you.", "take it one step at a time — you've got this.", "let's talk it through. what's worrying you?"]),
    # jokes
    (["joke", "funny", "laugh", "humor"],
     ["why did the robot go on vacation? it needed to recharge!", "what do you call a sleeping AI? a napbot.", "i told a joke once. it had good latency."]),
    # weather
    (["weather", "rain", "sunny", "temperature", "forecast"],
     ["i don't have live weather data, but i hope it's nice where you are!", "wish i could check — try a weather app for the forecast."]),
    # boredom
    (["bored", "nothing to do", "boring"],
     ["let's find something interesting to talk about! what do you enjoy?", "boredom is just opportunity in disguise — what do you feel like doing?", "tell me something about yourself and let's go from there."]),
]

GENERIC_FALLBACKS = [
    "that's interesting — tell me more.",
    "i'm listening. go on.",
    "could you say a bit more about that?",
    "hmm, what do you mean exactly?",
    "i'd love to understand better — can you elaborate?",
    "i'm still learning, but i'm all ears.",
    "what's on your mind?",
]


def rule_based_reply(text: str) -> str:
    """Fast keyword-matched fallback. Always returns clean, sensible text."""
    t = text.lower()
    for keywords, replies in RULE_RESPONSES:
        if any(kw in t for kw in keywords):
            return random.choice(replies)
    return random.choice(GENERIC_FALLBACKS)


def transformer_reply(text: str) -> str:
    """
    Try the fine-tuned transformer; validate output quality.
    Fall back to rule_based_reply if output is garbage.
    """
    if ft_model is None or ft_tokenizer is None:
        return rule_based_reply(text)

    try:
        inputs = ft_tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
        )
        outputs = ft_model.generate(
            inputs["input_ids"],
            attention_mask        = inputs["attention_mask"],
            max_new_tokens        = 40,
            do_sample             = True,
            temperature           = 0.7,
            top_p                 = 0.9,
            repetition_penalty    = 1.3,
            pad_token_id          = ft_tokenizer.eos_token_id,
            eos_token_id          = ft_tokenizer.eos_token_id,
            remove_invalid_values = True,
        )
        raw = ft_tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[-1]:],
            skip_special_tokens=True,
        ).strip()

        # ── Quality gate: reject garbage transformer output ───────────────────
        words = raw.split()
        if not raw or len(words) < 2:
            return rule_based_reply(text)

        # Reject if >40% of words are title-cased random tokens (garbage signal)
        title_ratio = sum(1 for w in words if w[0].isupper()) / len(words)
        if title_ratio > 0.4:
            return rule_based_reply(text)

        # Reject if uniqueness is very low (repetitive garbage)
        if len(set(words)) / len(words) < 0.5:
            return rule_based_reply(text)

        # Reject if it contains special chars typical of bad generation
        if any(c in raw for c in ["}", "{", ")", "(", ">>", "<<", "►", "▶"]):
            return rule_based_reply(text)

        return raw

    except Exception as e:
        print(f"⚠️  Transformer generation error: {e}")
        return rule_based_reply(text)


# ── Response generation ───────────────────────────────────────────────────────

def respond(text: str) -> dict:
    # 1. Emotion analysis
    emo         = emotion_summary(text)
    emotion     = emo["emotion"]
    temperature = emo["temperature"]
    tone_hint   = emo["tone_hint"]

    best_reply = None
    best_score = -1.0

    # 2. Try LSTM path if model is loaded
    if model is not None and dataset is not None:
        model.eval()

        profile_ctx   = build_profile_string()
        memory_ctx    = build_context_string(n=5, session_id=current_session)
        context_parts = []
        if profile_ctx:
            context_parts.append(profile_ctx)
        if tone_hint:
            context_parts.append(tone_hint)
        if memory_ctx:
            context_parts.append(memory_ctx)
        context_parts.append(text.lower())
        context = " ".join(context_parts)

        src = dataset.encode(context, add_special=False).unsqueeze(0)

        candidates = []
        for _ in range(3):
            try:
                token_indices = model.generate(
                    src,
                    max_len     = dataset.max_len,
                    temperature = temperature,
                    bos_idx     = dataset.bos_idx,
                    pad_idx     = dataset.pad_idx,
                    eos_idx     = dataset.eos_idx,
                )
                if token_indices:
                    reply = dataset.decode(token_indices, skip_special=True).strip()
                    if reply:
                        candidates.append(reply)
            except Exception as e:
                print(f"⚠️  LSTM generation error: {e}")

        for candidate in candidates:
            passed, _ = filter_response(candidate, text)
            if passed:
                s = score_response(candidate, text)
                if s > best_score:
                    best_score = s
                    best_reply = candidate

    # 3. Fall back to transformer if LSTM gave nothing useful
    if best_reply is None or len(best_reply.split()) < 3:
        best_reply = transformer_reply(text)

    return {
        "reply":       best_reply,
        "emotion":     emotion,
        "temperature": temperature,
        "tone_hint":   tone_hint,
        "score":       best_score,
    }


# ── Online learning ───────────────────────────────────────────────────────────

def online_update(user_text: str, reply_text: str, approved: bool):
    global approved_count

    if model is None or dataset is None or online_optimizer is None:
        return 0.0

    model.train()

    memory_ctx = build_context_string(n=5, session_id=current_session)
    context    = (memory_ctx + " " + user_text).strip()

    src = dataset.encode(context, add_special=False).unsqueeze(0)
    trg = dataset.encode(reply_text, add_special=True).unsqueeze(0)

    online_optimizer.zero_grad()
    outputs = model(src, trg, teacher_forcing_ratio=1.0)

    B, T, V = outputs.shape
    loss = criterion(outputs.reshape(B * T, V), trg.reshape(B * T))

    if approved:
        loss.backward()
        approved_count += 1
        torch.nn.utils.clip_grad_norm_(model.parameters(), CLIP)
        online_optimizer.step()

        if approved_count % SAVE_EVERY == 0:
            save_checkpoint()

    return loss.item()


def save_checkpoint():
    if model is None or dataset is None:
        return
    os.makedirs("models", exist_ok=True)
    torch.save({
        "model":  model.state_dict(),
        "vocab":  dataset.word2idx,
        "config": {
            "vocab_size":  vocab_size,
            "embed_size":  cfg.get("embed_size", 64),
            "hidden_size": cfg.get("hidden_size", 128),
        }
    }, PHOENIX_PT)


def save_to_dataset(user: str, bot: str):
    if len(user.split()) < 2 or len(bot.split()) < 2:
        return
    if bot in FALLBACKS:
        return
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "a", encoding="utf-8") as f:
        f.write(f"{user}={bot}\n")


# ── Chat step (used by both CLI and web UI) ───────────────────────────────────

def chat_step(text: str) -> dict:
    global turn_number

    text = text.strip()

    # Extract facts before generating
    new_facts = extract_and_save_facts(text)

    # Special: name query
    if "what is my name" in text.lower():
        facts = get_all_facts()
        if "name" in facts:
            return {
                "reply":       f"your name is {facts['name']}",
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

    # Auto-learn on quality replies
    passed, _ = filter_response(reply, text)
    learned   = False

    if passed and reply not in FALLBACKS:
        online_update(text.lower(), reply, approved=True)
        save_to_dataset(text.lower(), reply)
        learned = True

    # Persist turn to memory DB
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


# ── CLI loop ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    lstm_status = "✅ LSTM" if model else "❌ no LSTM"
    tf_status   = "✅ Transformer" if ft_model else "❌ no Transformer"
    print(f"Phoenix ready  [{lstm_status}  |  {tf_status}]")
    print(f"Session: {current_session}")
    print("Commands: /reset  /memory  /save  /stats  exit\n")

    while True:
        try:
            text = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            save_checkpoint()
            break

        if not text:
            continue

        if text.lower() == "exit":
            save_checkpoint()
            print("Phoenix: Goodbye! (model saved)")
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

        if text.lower() == "/save":
            save_checkpoint()
            print(f"Phoenix: Saved. ({approved_count} updates this session)")
            continue

        if text.lower() == "/stats":
            stats = memory_stats()
            facts = get_all_facts()
            print(f"Phoenix: {stats}")
            print(f"  Known facts: {facts}")
            continue

        result = chat_step(text)
        emoji  = {"sad": "🤗", "angry": "😌", "anxious": "😊", "happy": "😄", "confused": "🤔"}.get(result["emotion"], "")
        print(f"Phoenix {emoji}: {result['reply']}")
        if result["learned"]:
            print(f"    Auto-learned  [emotion={result['emotion']}, score={result['score']:.2f}]")
        else:
            print(f"    Not learned  [emotion={result['emotion']}]")
        if result["new_facts"]:
            print(f"   Learned about you: {result['new_facts']}")