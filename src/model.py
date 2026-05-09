import torch
import torch.nn as nn
import torch.nn.functional as F


class Encoder(nn.Module):
    def __init__(self, vocab_size, embed_size=64, hidden_size=128, dropout=0.3):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_size, padding_idx=0)
        self.lstm = nn.LSTM(embed_size, hidden_size, batch_first=True, bidirectional=True)
        self.dropout = nn.Dropout(dropout)
        self.fc_hidden = nn.Linear(hidden_size * 2, hidden_size)
        self.fc_cell   = nn.Linear(hidden_size * 2, hidden_size)

    def forward(self, x):
        embedded = self.dropout(self.embedding(x))
        outputs, (hidden, cell) = self.lstm(embedded)

        hidden = torch.cat([hidden[-2], hidden[-1]], dim=1)
        cell   = torch.cat([cell[-2],   cell[-1]],   dim=1)

        hidden = torch.tanh(self.fc_hidden(hidden)).unsqueeze(0)
        cell   = torch.tanh(self.fc_cell(cell)).unsqueeze(0)

        return outputs, hidden, cell


class Attention(nn.Module):
    def __init__(self, hidden_size):
        super().__init__()
        self.attn = nn.Linear(hidden_size * 3, hidden_size)
        self.v    = nn.Linear(hidden_size, 1, bias=False)

    def forward(self, hidden, encoder_outputs):
        B, src_len, _ = encoder_outputs.shape
        hidden = hidden.squeeze(0).unsqueeze(1).repeat(1, src_len, 1)

        energy    = torch.tanh(self.attn(torch.cat([hidden, encoder_outputs], dim=2)))
        attention = self.v(energy).squeeze(2)
        return F.softmax(attention, dim=1)


class Decoder(nn.Module):
    def __init__(self, vocab_size, embed_size=64, hidden_size=128, dropout=0.3):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_size, padding_idx=0)
        self.attention = Attention(hidden_size)
        self.lstm      = nn.LSTM(embed_size + hidden_size * 2, hidden_size, batch_first=True)
        self.fc_out    = nn.Linear(hidden_size * 3 + embed_size, vocab_size)
        self.dropout   = nn.Dropout(dropout)

    def forward(self, x, hidden, cell, encoder_outputs):
        x        = x.unsqueeze(1)
        embedded = self.dropout(self.embedding(x))

        attn_weights = self.attention(hidden, encoder_outputs).unsqueeze(1)
        context      = torch.bmm(attn_weights, encoder_outputs)

        lstm_input          = torch.cat([embedded, context], dim=2)
        output, (hidden, cell) = self.lstm(lstm_input, (hidden, cell))

        prediction = self.fc_out(
            torch.cat([output, context, embedded], dim=2).squeeze(1)
        )
        return prediction, hidden, cell, attn_weights.squeeze(1)


class PhoenixModel(nn.Module):

    def __init__(self, vocab_size, embed_size=64, hidden_size=128, dropout=0.3):
        super().__init__()
        self.encoder    = Encoder(vocab_size, embed_size, hidden_size, dropout)
        self.decoder    = Decoder(vocab_size, embed_size, hidden_size, dropout)
        self.vocab_size = vocab_size

    def forward(self, src, trg, teacher_forcing_ratio=0.5):
        B, trg_len = trg.shape
        outputs = torch.zeros(B, trg_len, self.vocab_size).to(src.device)

        encoder_outputs, hidden, cell = self.encoder(src)
        dec_input = trg[:, 0]

        for t in range(trg_len):
            prediction, hidden, cell, _ = self.decoder(dec_input, hidden, cell, encoder_outputs)
            outputs[:, t] = prediction

            if torch.rand(1).item() < teacher_forcing_ratio:
                dec_input = trg[:, t]
            else:
                dec_input = prediction.argmax(dim=1)

        return outputs

    def generate(self, src, max_len=10, temperature=0.8,
                 bos_idx=2, pad_idx=0, eos_idx=3):
        self.eval()

        with torch.no_grad():
            encoder_outputs, hidden, cell = self.encoder(src)
            dec_input = torch.tensor([bos_idx]).to(src.device)
            generated = []

            for _ in range(max_len):
                prediction, hidden, cell, _ = self.decoder(dec_input, hidden, cell, encoder_outputs)

                if temperature == 0:
                    dec_input = prediction.argmax(dim=1)
                else:
                    probs     = F.softmax(prediction / temperature, dim=1)
                    dec_input = torch.multinomial(probs, num_samples=1).squeeze(1)

                token = dec_input.item()

                if token == eos_idx or token == pad_idx:
                    break
                if token in generated[-3:]:
                    continue

                generated.append(token)

        return generated