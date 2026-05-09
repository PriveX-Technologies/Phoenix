import torch
import torch.nn as nn
import torch.optim as optim
import os
import random
from tqdm import tqdm

from model import PhoenixModel
from dataset import PhoenixDataset

# ── Reproducibility ───────────────────────────────────────────────────────────
SEED = 42
random.seed(SEED)
torch.manual_seed(SEED)

# ── Config ────────────────────────────────────────────────────────────────────
EPOCHS          = 1900
BATCH_SIZE      = 128
LR              = 3e-4
TEACHER_FORCING = 0.9
CLIP            = 1.0
VAL_SPLIT       = 0.05
SAVE_PATH       = "models/phoenix.pt"
EMBED_SIZE      = 64    # frozen — never change after first train
HIDDEN_SIZE     = 128   # frozen — never change after first train

# ── Data ──────────────────────────────────────────────────────────────────────
dataset = PhoenixDataset()
print(dataset)

X, y  = dataset.get_data()
n     = len(X)
n_val = max(1, int(n * VAL_SPLIT))

indices = list(range(n))
random.shuffle(indices)
val_idx, trn_idx = indices[:n_val], indices[n_val:]

X_trn, y_trn = X[trn_idx], y[trn_idx]
X_val, y_val = X[val_idx], y[val_idx]
print(f"Train: {len(X_trn)} pairs | Val: {len(X_val)} pairs")

# ── Model ─────────────────────────────────────────────────────────────────────
vocab_size = len(dataset.vocab)
model = PhoenixModel(vocab_size, embed_size=EMBED_SIZE, hidden_size=HIDDEN_SIZE)

# ── Continuous learning: resume from checkpoint if vocab matches ───────────────
resumed = False
if os.path.exists(SAVE_PATH):
    print("🔄 Found existing model — attempting to resume...")
    checkpoint     = torch.load(SAVE_PATH, map_location="cpu")
    saved_vocab_sz = checkpoint["config"].get("vocab_size", 0)

    if saved_vocab_sz == vocab_size:
        try:
            model.load_state_dict(checkpoint["model"])
            print("✅ Resumed. Training on top of existing knowledge.")
            resumed = True
        except Exception as e:
            print(f"⚠️  Load failed ({e}). Starting fresh.")
    else:
        print(f"⚠️  Vocab changed ({saved_vocab_sz} → {vocab_size}). Fresh start.")
        old_path = SAVE_PATH.replace(".pt", "_old.pt")

        if os.path.exists(old_path):
            os.remove(old_path)

        os.rename(SAVE_PATH, old_path)

# ── Word2Vec embedding init (fresh starts only) ───────────────────────────────
if not resumed:
    print("🔥 Building Word2Vec embeddings...")
    try:
        from gensim.models import Word2Vec

        sentences = []
        for inp, out in dataset.pairs:
            sentences.append(inp.split())
            sentences.append(out.split())

        w2v = Word2Vec(vector_size=EMBED_SIZE, window=5, min_count=1, workers=4, seed=42)
        w2v.build_vocab(sentences)
        w2v.train(sentences, total_examples=w2v.corpus_count, epochs=w2v.epochs)

        matrix = torch.zeros(vocab_size, EMBED_SIZE)
        for word, idx in dataset.word2idx.items():
            if word in w2v.wv:
                matrix[idx] = torch.tensor(w2v.wv[word], dtype=torch.float)
            else:
                matrix[idx] = torch.randn(EMBED_SIZE) * 0.01

        model.encoder.embedding.weight.data.copy_(matrix)
        model.decoder.embedding.weight.data.copy_(matrix)
        print("✅ Word2Vec embeddings loaded.")

    except ImportError:
        print("⚠️  gensim not installed — using random embeddings. Run: pip install gensim")
    except Exception as e:
        print(f"⚠️  Word2Vec failed ({e}) — using random embeddings.")

# ── Optimiser & loss ──────────────────────────────────────────────────────────
criterion = nn.CrossEntropyLoss(ignore_index=dataset.pad_idx)
optimizer = optim.Adam(model.parameters(), lr=LR)
scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=5)

# ── Training loop ─────────────────────────────────────────────────────────────
best_val_loss = float("inf")

for epoch in range(1, EPOCHS + 1):
    model.train()

    perm       = torch.randperm(len(X_trn))
    epoch_loss = 0.0
    n_batches  = 0

    loop = tqdm(range(0, len(X_trn), BATCH_SIZE), desc=f"Epoch {epoch}/{EPOCHS}")

    for i in loop:
        batch_idx = perm[i : i + BATCH_SIZE]
        src, trg  = X_trn[batch_idx], y_trn[batch_idx]

        optimizer.zero_grad()
        outputs = model(src, trg, teacher_forcing_ratio=TEACHER_FORCING)

        B, T, V = outputs.shape
        loss = criterion(outputs.reshape(B * T, V), trg.reshape(B * T))

        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), CLIP)
        optimizer.step()

        epoch_loss += loss.item()
        n_batches  += 1
        loop.set_postfix(loss=f"{loss.item():.3f}", lr=f"{optimizer.param_groups[0]['lr']:.5f}")

    avg_train_loss = epoch_loss / n_batches

    # ── Validation ────────────────────────────────────────────────────────────
    model.eval()
    val_loss, val_batches = 0.0, 0

    with torch.no_grad():
        for i in range(0, len(X_val), BATCH_SIZE):
            src, trg = X_val[i:i+BATCH_SIZE], y_val[i:i+BATCH_SIZE]
            outputs  = model(src, trg, teacher_forcing_ratio=0.0)
            B, T, V  = outputs.shape
            loss     = criterion(outputs.reshape(B * T, V), trg.reshape(B * T))
            val_loss    += loss.item()
            val_batches += 1

    val_loss = val_loss / val_batches
    scheduler.step(val_loss)
    print(f"✅ Epoch {epoch}/{EPOCHS} | Train: {avg_train_loss:.4f} | Val: {val_loss:.4f}")

    if val_loss < best_val_loss:
        best_val_loss = val_loss
        os.makedirs(os.path.dirname(SAVE_PATH), exist_ok=True)
        torch.save({
            "model": model.state_dict(),
            "vocab": dataset.word2idx,
            "config": {"vocab_size": vocab_size, "embed_size": EMBED_SIZE, "hidden_size": HIDDEN_SIZE}
        }, SAVE_PATH)
        print(f"   💾 Saved best model (val: {val_loss:.4f})")

print(f"\nTraining complete. Best val loss: {best_val_loss:.4f}")
print(f"Model saved to {SAVE_PATH}")