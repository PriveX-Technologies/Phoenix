# 🔥 Phoenix AI

A cinematic, cyberpunk AI companion with a custom LSTM seq2seq model,
optional DialoGPT fine-tuning, emotion detection, SQLite memory, and a
beautiful dark-UI frontend that talks directly to your local Flask backend.

---

## 📁 Project Structure

```
phoenix/
├── src/
│   ├── model.py          — LSTM Encoder-Decoder + Attention
│   ├── dataset.py        — Vocab builder + tokenizer + pair loader
│   ├── train.py          — Full training loop (Word2Vec init, val, checkpoint)
│   ├── inference.py      — Chat engine: LSTM → Transformer → rule-based fallback
│   ├── emotion.py        — Regex emotion detector + temperature/tone mapping
│   ├── memory.py         — SQLite memory: facts, turns, sessions
│   ├── filters.py        — Response quality filter + scorer
│   ├── fine_tune.py      — Fine-tune DialoGPT-medium on your data
│   ├── prepare_data.py   — Download DailyDialog / Cornell / BlendedSkillTalk
│   ├── dataset_builder.py— Expanded dataset builder (6 sources + seed data)
│   ├── generate_data.py  — Hand-crafted training pair generator
│   └── web_ui.py         — Flask REST API (chat, facts, stats, history, save…)
├── data/
│   └── real_data.txt     — Training pairs (input=output, one per line)
├── models/
│   ├── phoenix.pt        — Trained LSTM checkpoint
│   └── phoenix_transformer/  — Fine-tuned DialoGPT (optional)
├── frontend/
│   └── phoenix.html      — Full cyberpunk UI (open in browser)
├── requirements.txt
└── README.md
```

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Build training data
```bash
# Option A — fast seed + online datasets (recommended):
python src/dataset_builder.py

# Option B — hand-crafted pairs only (offline, no downloads):
python src/generate_data.py

# Option C — original prepare_data.py (Cornell + DailyDialog):
python src/prepare_data.py
```

### 3. Train the LSTM model
```bash
python src/train.py
# → saves models/phoenix.pt
# Typical: 3 epochs, ~5 min on CPU for 15k pairs
```

### 4. (Optional) Fine-tune DialoGPT
```bash
python src/fine_tune.py
# → saves models/phoenix_transformer/
# Requires GPU for reasonable speed
```

### 5. Start the Flask backend
```bash
python src/web_ui.py
# → http://localhost:5000
```

### 6. Open the frontend
Open `frontend/phoenix.html` directly in your browser.
- Make sure **"Use Local Phoenix Model"** is ON in Settings
- The backend URL is `http://localhost:5000` (change in the HTML if needed)

---

## 🌐 API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/chat` | Send a message, get `{reply, emotion, tone_hint, learned, new_facts, score}` |
| GET | `/facts` | All extracted facts from memory.py |
| GET | `/stats` | Memory stats: `{total_turns, total_facts, sessions}` |
| GET | `/history` | Recent turns for current session |
| GET | `/memory?n=20` | Last N conversation turns |
| POST | `/reset_session` | Clear current session memory (keeps facts) |
| POST | `/save` | Force-save LSTM checkpoint |
| GET | `/status` | Backend health: `{lstm_loaded, transformer_loaded, session_id, approved_count}` |

---

## 💡 Frontend Features

- 🔥 **Dual-mode**: Phoenix LSTM backend OR Claude API fallback (toggle in Settings)
- 🧠 **Live memory panel**: see facts extracted by `memory.py` in real-time
- 📜 **History panel**: browse all turns stored in SQLite this session
- 😊 **Emotion-reactive UI**: colours sync with `emotion.py` output
- 💾 **Auto-learn badges**: see which turns were reinforced by online learning
- ★ **Score display**: `filters.py` quality score shown on every reply
- 🔊 **Voice I/O**: SpeechRecognition + SpeechSynthesis APIs
- 📎 **Image upload**: send images for vision (Claude fallback mode)
- 🎨 **5 colour themes**: Purple, Cyan, Pink, Amber, Green

### Slash commands (type in chat)
| Command | Action |
|---------|--------|
| `/reset` | Clear session memory on backend + frontend |
| `/stats` | Show memory stats in chat |
| `/facts` | Open the facts panel |
| `/help` | List all commands |

---

## 🧠 How inference.py Works

```
User input
    ↓
emotion.py  →  emotion + temperature + tone_hint
    ↓
memory.py   →  profile string + conversation context
    ↓
LSTM model  →  3 candidate replies (beam-like sampling)
    ↓
filters.py  →  quality check + score each candidate
    ↓
Best reply? ──yes──→ return + online_update() + save_to_dataset()
    ↓ no
transformer_reply()  →  fine-tuned DialoGPT (if available)
    ↓ garbage/missing
rule_based_reply()   →  keyword-matched clean fallback
```

---

## 🔧 Configuration

Edit top of `inference.py`:
```python
LR_ONLINE  = 5e-5    # online learning rate
SAVE_EVERY = 10      # checkpoint every N approved turns
```

Edit top of `train.py`:
```python
EPOCHS     = 3
BATCH_SIZE = 128
LR         = 3e-4
EMBED_SIZE = 64      # ← never change after first train
HIDDEN_SIZE= 128     # ← never change after first train
```

In `phoenix.html` (top of script block):
```javascript
const BACKEND_URL = "http://localhost:5000";  // your Flask server
const USE_BACKEND = true;   // false = Claude API fallback
```

---

## 📈 Continuous Learning

Every approved reply is:
1. Used for one gradient step via `online_update()` (live weight update)
2. Appended to `data/real_data.txt` (grows your training set)
3. Stored in SQLite via `memory.py` (conversation history)

After collecting more data, re-run `train.py` to retrain from scratch with
the expanded dataset. The checkpoint format is stable — vocab changes trigger
a safe rename of the old model.

---

## 🛠 Troubleshooting

**"Cannot reach Phoenix backend"**
→ Run `python src/web_ui.py` first. Check port 5000 is free.

**"Phoenix checkpoint not found"**
→ Run `python src/train.py` to generate `models/phoenix.pt`.

**Replies are garbage / all `<unk>`**
→ Vocab mismatch. Delete `models/phoenix.pt` and retrain.

**Voice not working**
→ Use Chrome or Edge. Firefox has limited SpeechSynthesis support.

**CORS errors in browser console**
→ Already handled by `web_ui.py`'s `@app.after_request` CORS headers.

---

*Phoenix AI — Built with PyTorch, Flask, and a lot of neon purple. ✦*