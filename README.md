# Phoenix AI — Ollama / Qwen Backend

> **Migration note:** The LSTM + fine-tuned transformer pipeline has been
> replaced with a locally-running [Ollama](https://ollama.com) server using
> the **Qwen 2.5** model family.  All other Phoenix systems are unchanged:
> emotion detection, memory (SQLite), persona post-processing, dataset
> logging, and the web UI.

---

## Quick-start

```bash
# 1. Install Ollama  (https://ollama.com/download)
#    macOS:   brew install ollama
#    Linux:   curl -fsSL https://ollama.com/install.sh | sh

# 2. Pull the model (run once)
ollama pull qwen2.5          # ~4 GB — fast, great quality
# Or a larger variant:
# ollama pull qwen2.5:14b
# ollama pull qwen2.5:72b

# 3. Make sure Ollama is running
ollama serve                 # keep this terminal open (or it auto-starts on macOS)

# 4. Install Python deps
pip install -r requirements.txt

# 5. Launch Phoenix
python main.py               # opens http://localhost:5000 automatically
```

---

## Configuration

Override defaults via environment variables:

| Variable       | Default                   | Description                       |
|----------------|---------------------------|-----------------------------------|
| `OLLAMA_HOST`  | `http://localhost:11434`  | Ollama server URL                 |
| `OLLAMA_MODEL` | `qwen2.5`                 | Model tag (any Qwen variant works) |

```bash
OLLAMA_MODEL=qwen2.5:14b python main.py
```

---

## What changed

| File                   | Change                                                                 |
|------------------------|------------------------------------------------------------------------|
| `src/inference.py`     | **Replaced** — now calls Ollama `/api/chat` instead of LSTM/transformer |
| `src/web_ui.py`        | `/status` endpoint updated to report Ollama readiness                  |
| `main.py`              | Removed dataset/training bootstrap; added Ollama pre-flight check      |
| `requirements.txt`     | Replaced PyTorch / HuggingFace deps with `flask` + `requests`          |

All other files (`emotion.py`, `memory.py`, `filters.py`, `dataset.py`,
`train.py`, `fine_tune.py`, frontend) are **untouched**.

---

## Memory & personality

Phoenix still:
- Detects emotion and adjusts tone automatically
- Saves facts about you (name, age, location …) in `data/phoenix_memory.db`
- Applies the Phoenix voice persona (fillers, continuations, thinking pauses)
- Logs good conversations to `data/real_data.txt` for future fine-tuning

---

## Switching models

Any Ollama-supported model works.  Qwen variants recommended for quality:

```bash
ollama pull qwen2.5          # default – 4 GB, fast
ollama pull qwen2.5:14b      # better reasoning – 9 GB
ollama pull qwen2.5:72b      # best quality – 45 GB
```

Then launch with:
```bash
OLLAMA_MODEL=qwen2.5:14b python main.py
```
