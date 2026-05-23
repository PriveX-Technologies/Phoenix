from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    Trainer,
    TrainingArguments,
    DataCollatorForLanguageModeling,
)
from datasets import Dataset
import torch
import os

# ── Load model & tokenizer ────────────────────────────────────────────────────
model_name = "microsoft/DialoGPT-medium"
print(f"Loading {model_name}...")

tokenizer = AutoTokenizer.from_pretrained(model_name)

special_tokens = {
    "additional_special_tokens": [
        "<|user|>",
        "<|assistant|>"
    ]
}

tokenizer.add_special_tokens(special_tokens)
tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(model_name)
model.resize_token_embeddings(len(tokenizer))

# ── Load dataset ──────────────────────────────────────────────────────────────
DATA_FILE = "data/real_data.txt"
SAVE_PATH = "models/phoenix_transformer"

if not os.path.exists(DATA_FILE):
    print(f"❌ Dataset not found at {DATA_FILE}")
    print("   Run: python src/prepare_data.py first")
    exit(1)

data = []
with open(DATA_FILE, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if "=" in line:
            user, bot = line.split("=", 1)
            text = (
                f"<|user|>\n"
                f"{user.strip()}\n"
                f"<|assistant|>\n"
                f"{bot.strip()}\n"
            )
            data.append({"text": text})

print(f"Loaded {len(data)} conversation pairs.")
dataset = Dataset.from_list(data)

# ── Tokenize — CRITICAL: set labels = input_ids for loss computation ──────────
def tokenize(example):
    encoded = tokenizer(
        example["text"],
        truncation=True,
        padding="max_length",
        max_length=128,
    )
    encoded["labels"] = [
        -100 if token == tokenizer.pad_token_id else token
        for token in encoded["input_ids"]
    ]
    return encoded

print("Tokenizing dataset...")
tokenized = dataset.map(tokenize, remove_columns=["text"])

# ── Data collator ─────────────────────────────────────────────────────────────
data_collator = DataCollatorForLanguageModeling(
    tokenizer=tokenizer,
    mlm=False,
)

# ── Training config ───────────────────────────────────────────────────────────
training_args = TrainingArguments(
    output_dir                  = "./phoenix_ft_checkpoints",
    per_device_train_batch_size = 2,
    num_train_epochs            = 3,
    max_steps                   = 19,
    save_steps                  = 500,
    logging_steps               = 50,
    fp16                        = False,
    dataloader_pin_memory       = False,
    report_to                   = "none",
    save_total_limit            = 2,
    logging_dir                 = "./phoenix_ft_logs",
)

# ── Trainer ───────────────────────────────────────────────────────────────────
trainer = Trainer(
    model         = model,
    args          = training_args,
    train_dataset = tokenized,
    data_collator = data_collator,
)

# ── Train ─────────────────────────────────────────────────────────────────────
print("\n🔥 Starting fine-tuning...")
trainer.train()

# ── Save ──────────────────────────────────────────────────────────────────────
os.makedirs(SAVE_PATH, exist_ok=True)
model.save_pretrained(SAVE_PATH)
tokenizer.save_pretrained(SAVE_PATH)
print(f"\n✅ Fine-tuned model saved to {SAVE_PATH}")