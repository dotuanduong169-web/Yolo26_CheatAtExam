from pathlib import Path
from collections import Counter

root = Path(r"D:\AI_KLTN\dataset_seg_v3")

classes = {
    0: "Answer_paper",
    1: "Cheat_Paper",
    2: "cellphone",
    3: "earphone",
    4: "smartwatch"
}

for split in ["train", "valid"]:

    img_dir = root / split / "images"
    lbl_dir = root / split / "labels"

    images = {p.stem for p in img_dir.iterdir() if p.is_file()}
    labels = {p.stem for p in lbl_dir.iterdir() if p.is_file()}

    missing_labels = images - labels
    orphan_labels = labels - images

    counter = Counter()
    bad = []
    empty = []

    for f in lbl_dir.glob("*.txt"):
        text = f.read_text(encoding="utf-8").strip()

        if not text:
            empty.append(f.name)
            continue

        for line_no, line in enumerate(text.splitlines(), 1):
            parts = line.split()

            if len(parts) < 7:
                bad.append(
                    f"{f.name}: line {line_no}: TOO_FEW_VALUES ({len(parts)})"
                )
                continue

            try:
                cls = int(float(parts[0]))
                coords = [float(x) for x in parts[1:]]
            except:
                bad.append(
                    f"{f.name}: line {line_no}: NON_NUMERIC"
                )
                continue

            if cls not in classes:
                bad.append(
                    f"{f.name}: line {line_no}: INVALID_CLASS {cls}"
                )
                continue

            if len(coords) % 2 != 0:
                bad.append(
                    f"{f.name}: line {line_no}: ODD_COORDINATES"
                )
                continue

            if len(coords) < 6:
                bad.append(
                    f"{f.name}: line {line_no}: NOT_ENOUGH_POLYGON_POINTS"
                )
                continue

            if any(x < 0 or x > 1 for x in coords):
                bad.append(
                    f"{f.name}: line {line_no}: COORD_OUT_OF_RANGE"
                )
                continue

            counter[cls] += 1

    print("\n" + "=" * 50)
    print(split.upper())
    print("=" * 50)

    print(f"Images       : {len(images)}")
    print(f"Labels       : {len(labels)}")
    print(f"Missing label: {len(missing_labels)}")
    print(f"Orphan label : {len(orphan_labels)}")
    print(f"Empty label  : {len(empty)}")
    print(f"Bad lines    : {len(bad)}")

    print("\nOBJECT DISTRIBUTION:")

    total = 0

    for cls in range(5):
        n = counter[cls]
        total += n
        print(f"{cls} - {classes[cls]:15s}: {n}")

    print(f"TOTAL OBJECTS              : {total}")

    if missing_labels:
        print("\nFIRST MISSING LABELS:")
        for x in sorted(missing_labels)[:10]:
            print(x)

    if orphan_labels:
        print("\nFIRST ORPHAN LABELS:")
        for x in sorted(orphan_labels)[:10]:
            print(x)

    if empty:
        print("\nFIRST EMPTY LABELS:")
        for x in empty[:10]:
            print(x)

    if bad:
        print("\nFIRST BAD LINES:")
        for x in bad[:20]:
            print(x)

print("\n" + "=" * 50)
print("FINAL DATASET CHECK COMPLETED")
print("=" * 50)