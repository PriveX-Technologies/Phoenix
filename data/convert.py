input_file = "dialogues_text.txt"
output_file = "real_data.txt"

with open(input_file, "r", encoding="utf-8") as f:
    lines = [line.strip() for line in f if line.strip()]

pairs = []

# 🔥 create pairs from consecutive lines
for i in range(len(lines) - 1):
    inp = lines[i]
    out = lines[i + 1]

    # basic cleaning
    if len(inp.split()) > 2 and len(out.split()) > 2:
        pairs.append(f"{inp.lower()} = {out.lower()}")

with open(output_file, "w", encoding="utf-8") as f:
    for p in pairs:
        f.write(p + "\n")

print(f"✅ Created {len(pairs)} training pairs")