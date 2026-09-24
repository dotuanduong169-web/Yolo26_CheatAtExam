from pathlib import Path

root = Path(r".\realworld_data\train\labels")

counts = {
    0: 0,  # Answer_paper
    1: 0,  # Cheat_Paper
    2: 0,  # cellphone
}

errors = []
files = 0
empty = 0

for f in root.glob("*.txt"):
    files += 1
    lines = f.read_text(encoding="utf-8").splitlines()

    if not lines:
        empty += 1
        continue

    for line_no, line in enumerate(lines, 1):
        parts = line.split()

        try:
            cls = int(parts[0])
            values = list(map(float, parts[1:]))
        except Exception:
            errors.append(
                f"{f.name}: line {line_no} - invalid format"
            )
            continue

        if cls not in counts:
            errors.append(
                f"{f.name}: line {line_no} - invalid class {cls}"
            )
            continue

        counts[cls] += 1

        # YOLO segmentation:
        # class x1 y1 x2 y2 x3 y3 ...
        if len(values) < 6:
            errors.append(
                f"{f.name}: line {line_no} - too few coordinates"
            )
        elif len(values) % 2 != 0:
            errors.append(
                f"{f.name}: line {line_no} - odd number of coordinates"
            )
        elif any(v < 0 or v > 1 for v in values):
            errors.append(
                f"{f.name}: line {line_no} - coordinate out of range"
            )

print("===== REALWORLD DATA CHECK =====")
print(f"Label files   : {files}")
print(f"Empty labels  : {empty}")
print()
print(f"Answer_paper  : {counts[0]}")
print(f"Cheat_Paper   : {counts[1]}")
print(f"cellphone     : {counts[2]}")
print(f"Total objects : {sum(counts.values())}")
print()
print(f"Errors        : {len(errors)}")

if errors:
    print("\n===== FIRST ERRORS =====")
    for error in errors[:20]:
        print(error)
else:
    print("\nAll labels are valid.")