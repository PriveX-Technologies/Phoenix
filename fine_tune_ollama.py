"""
fine_tune_ollama.py  –  Phoenix fine-tune pipeline (Ollama Modelfile approach)

Reads accumulated conversations from data/real_data.txt and bakes them into
a custom Ollama model called "phoenix-ft" using a Modelfile with embedded
system prompt + few-shot examples from real_data.txt.

Usage
-----
    python fine_tune_ollama.py                   # uses data/real_data.txt
    python fine_tune_ollama.py --data my_data.txt --model qwen2.5:14b --out phoenix-ft-v2
    python fine_tune_ollama.py --status          # check how many pairs are available

Requirements
------------
    ollama serve   (must be running)
    pip install requests

How it works
------------
Ollama doesn't support LoRA fine-tuning directly, but you CAN embed a rich
system prompt + curated few-shot examples into a Modelfile.  This pipeline:
  1. Reads real_data.txt  (format: user_text=bot_text per line)
  2. Selects the N best/most diverse examples
  3. Writes a Modelfile with those examples as few-shot turns
  4. Calls `ollama create phoenix-ft -f Modelfile`

The resulting model is a Qwen variant with Phoenix's exact conversation style
baked in.  Switch to it with:  OLLAMA_MODEL=phoenix-ft python main.py
"""

import argparse
import os
import pathlib
import random
import subprocess
import sys
import textwrap

# ── Config ────────────────────────────────────────────────────────────────────
DEFAULT_DATA  = "data/real_data.txt"
DEFAULT_BASE  = os.environ.get("OLLAMA_MODEL", "qwen2.5")
DEFAULT_OUT   = "phoenix-ft"
MAX_EXAMPLES  = 40   # how many few-shot pairs to embed (keep Modelfile small)
MIN_PAIRS     = 10   # warn if fewer than this many pairs available

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


def load_pairs(path: str) -> list[tuple[str, str]]:
    """Load user=bot pairs from real_data.txt. Returns list of (user, bot) tuples."""
    p = pathlib.Path(path)
    if not p.exists() or p.stat().st_size == 0:
        return []
    pairs = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if "=" not in line:
            continue
        user, _, bot = line.partition("=")
        user, bot = user.strip(), bot.strip()
        # Quality gate: both sides must have at least 3 words
        if len(user.split()) >= 3 and len(bot.split()) >= 3:
            pairs.append((user, bot))
    return pairs


def select_examples(pairs: list, n: int) -> list[tuple[str, str]]:
    """Pick a diverse sample — prefer longer, higher-quality exchanges."""
    if len(pairs) <= n:
        return pairs
    # Score by combined word count (longer = richer example)
    scored = sorted(pairs, key=lambda p: len(p[0].split()) + len(p[1].split()),
                    reverse=True)
    # Take top half by length, rest random
    top    = scored[: n // 2]
    rest   = random.sample(scored[n // 2:], min(n - len(top), len(scored[n // 2:])))
    sample = top + rest
    random.shuffle(sample)
    return sample


def build_modelfile(base_model: str, examples: list[tuple[str, str]]) -> str:
    """Generate the Ollama Modelfile content."""
    lines = [
        f"FROM {base_model}",
        "",
        f'SYSTEM """{SYSTEM_PROMPT.strip()}"""',
        "",
        "# ── Few-shot examples from real Phoenix conversations ─────────────",
    ]
    for user, bot in examples:
        lines.append(f'MESSAGE user "{user}"')
        lines.append(f'MESSAGE assistant "{bot}"')
        lines.append("")

    lines += [
        "# ── Generation parameters ───────────────────────────────────────────",
        "PARAMETER temperature 0.35",
        "PARAMETER top_p 0.85",
        "PARAMETER repeat_penalty 1.4",
        "PARAMETER num_predict 80",
    ]
    return "\n".join(lines)


def create_model(modelfile_path: str, output_name: str) -> bool:
    """Run `ollama create` and stream output."""
    print(f"\n🔨 Creating Ollama model '{output_name}'...")
    result = subprocess.run(
        ["ollama", "create", output_name, "-f", modelfile_path],
        capture_output=False,   # stream to terminal
    )
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Phoenix fine-tune pipeline (Modelfile)")
    parser.add_argument("--data",   default=DEFAULT_DATA,  help="Path to real_data.txt")
    parser.add_argument("--model",  default=DEFAULT_BASE,  help="Base Ollama model to use")
    parser.add_argument("--out",    default=DEFAULT_OUT,   help="Output model name")
    parser.add_argument("--max",    type=int, default=MAX_EXAMPLES, help="Max few-shot examples")
    parser.add_argument("--status", action="store_true",   help="Show data stats and exit")
    args = parser.parse_args()

    # ── Load data ─────────────────────────────────────────────────────────────
    pairs = load_pairs(args.data)

    if args.status:
        print(f"📊 Data file   : {args.data}")
        print(f"   Total pairs : {len(pairs)}")
        print(f"   Ready       : {'✅ yes' if len(pairs) >= MIN_PAIRS else f'⚠️  need at least {MIN_PAIRS}'}")
        sys.exit(0)

    if not pairs:
        print(f"❌ No data found at '{args.data}'.")
        print("   Chat with Phoenix first — good conversations are saved automatically.")
        sys.exit(1)

    if len(pairs) < MIN_PAIRS:
        print(f"⚠️  Only {len(pairs)} pairs available (recommended: {MIN_PAIRS}+).")
        print("   Fine-tuning anyway, but more data = better results.")

    print(f"📦 Loaded {len(pairs)} conversation pairs from '{args.data}'")

    # ── Select examples ───────────────────────────────────────────────────────
    examples = select_examples(pairs, args.max)
    print(f"✂️  Selected {len(examples)} examples for Modelfile")

    # ── Write Modelfile ───────────────────────────────────────────────────────
    modelfile_content = build_modelfile(args.model, examples)
    modelfile_path    = "Modelfile.phoenix"
    pathlib.Path(modelfile_path).write_text(modelfile_content, encoding="utf-8")
    print(f"📝 Modelfile written → {modelfile_path}")

    # ── Create model ──────────────────────────────────────────────────────────
    ok = create_model(modelfile_path, args.out)

    if ok:
        print(f"\n✅ Model '{args.out}' created successfully!")
        print(f"\nTo use it:")
        print(f"   OLLAMA_MODEL={args.out} python main.py")
        print(f"\nOr set it permanently in your shell:")
        print(f"   export OLLAMA_MODEL={args.out}")
    else:
        print(f"\n❌ Model creation failed.")
        print("   Make sure Ollama is running:  ollama serve")
        sys.exit(1)


if __name__ == "__main__":
    main()
