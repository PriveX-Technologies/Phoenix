import re
import torch
import os


class PhoenixDataset:
    PAD = "<pad>"
    UNK = "<unk>"
    BOS = "<bos>"
    EOS = "<eos>"
    SPECIAL_TOKENS = [PAD, UNK, BOS, EOS]

    def __init__(self, path=None, max_len=80):
        self.max_len = max_len
        self.pairs   = []

        # ✅ FIXED PATH (always correct)
        if path is None:
            base = os.path.dirname(os.path.dirname(__file__))
            path = os.path.join(base, "data", "real_data.txt")

        print(f"📂 Loading dataset from: {path}")

        vocab_words = set()

        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line in lines:
            line = line.strip()
            if not line or "=" not in line:
                continue
            inp, out = line.split("=", 1)
            inp = self._clean(inp)
            out = self._clean(out)
            if not inp or not out:
                continue
            self.pairs.append((inp, out))
            for w in inp.split():
                vocab_words.add(w)
            for w in out.split():
                vocab_words.add(w)

        # Build vocab
        self.vocab    = self.SPECIAL_TOKENS + sorted(vocab_words)
        self.word2idx = {w: i for i, w in enumerate(self.vocab)}
        self.idx2word = {i: w for w, i in self.word2idx.items()}

        self.pad_idx = self.word2idx[self.PAD]
        self.unk_idx = self.word2idx[self.UNK]
        self.bos_idx = self.word2idx[self.BOS]
        self.eos_idx = self.word2idx[self.EOS]

        
    # ── Text helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _clean(text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"[^a-z0-9\s]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _tokenize(self, sentence: str):
        return sentence.split()

    # ── Encoding / Decoding ───────────────────────────────────────────────────

    def encode(self, sentence: str, add_special=False) -> torch.Tensor:
        tokens  = self._tokenize(self._clean(sentence))
        indices = [self.word2idx.get(w, self.unk_idx) for w in tokens]

        if add_special:
            indices = [self.bos_idx] + indices + [self.eos_idx]

        indices = indices[: self.max_len]
        indices += [self.pad_idx] * (self.max_len - len(indices))

        return torch.tensor(indices, dtype=torch.long)

    def decode(self, indices, skip_special=True) -> str:
        words   = []
        special = {self.pad_idx, self.bos_idx, self.eos_idx} if skip_special else set()

        for idx in indices:
            idx = idx.item() if hasattr(idx, "item") else int(idx)
            if idx == self.eos_idx:
                break
            if idx in special:
                continue
            words.append(self.idx2word.get(idx, self.UNK))

        return " ".join(words)

    # ── Dataset ───────────────────────────────────────────────────────────────

    def get_data(self):
        X, y = [], []
        for inp, out in self.pairs:
            X.append(self.encode(inp, add_special=False))
            y.append(self.encode(out, add_special=True))
        return torch.stack(X), torch.stack(y)

    def __len__(self):
        return len(self.pairs)

    def __repr__(self):
        return (
            f"PhoenixDataset(pairs={len(self.pairs)}, "
            f"vocab_size={len(self.vocab)}, max_len={self.max_len})"
        )