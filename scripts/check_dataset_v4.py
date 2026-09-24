from pathlib import Path

ROOT = Path(r"D:\AI_KLTN\dataset_seg_v4")

CLASS_NAMES = {
    0: "Answer_paper",
    1: "Cheat_Paper",
    2: "cellphone",
}

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

total_images = 0
total_labels = 0
empty_labels = 0
bad_lines = 0
bad_class = 0
bad_coords = 0
objects = {0: 0, 1: 0, 2: 0}

print("=" * 60)
print("DATASET V4 CHECK")
print("=" * 60)

for split in ["train", "valid", "test"]:
    image_dir = ROOT / split / "images"
    label_dir = ROOT / split / "labels"

    images = {
        p.stem
        for p in image_dir.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    }

    labels = {
        p.stem
        for p in label_dir.glob("*.txt")
    }

    missing = images - labels
    orphan = labels - images

    print(f"\n[{split.upper()}]")
    print("Images :", len(images))
    print("Labels :", len(labels))
    print("Missing labels:", len(missing))
    print("Orphan labels :", len(orphan))

    total_images += len(images)
    total_labels += len(labels)

    for label_file in label_dir.glob("*.txt"):
        text = label_file.read_text(encoding="utf-8").strip()

        if not text:
            empty_labels += 1
            continue

        for line_no, line in enumerate(text.splitlines(), 1):
            parts = line.split()

            # Segmentation:
            # class + x1 y1 x2 y2 ... xn yn
            if len(parts) < 7:
                print(
                    f"BAD LINE: {label_file.name}:{line_no} "
                    f"-> too few values"
                )
                bad_lines += 1
                continue

            try:
                cls = int(parts[0])
            except ValueError:
                print(
                    f"BAD CLASS: {label_file.name}:{line_no}"
                )
                bad_class += 1
                continue

            if cls not in CLASS_NAMES:
                print(
                    f"INVALID CLASS {cls}: "
                    f"{label_file.name}:{line_no}"
                )
                bad_class += 1
                continue

            coords = parts[1:]

            if len(coords) % 2 != 0:
                print(
                    f"BAD COORDINATES: "
                    f"{label_file.name}:{line_no}"
                )
                bad_coords += 1
                continue

            try:
                values = [float(x) for x in coords]
            except ValueError:
                print(
                    f"NON-NUMERIC COORDINATES: "
                    f"{label_file.name}:{line_no}"
                )
                bad_coords += 1
                continue

            if any(v < 0 or v > 1 for v in values):
                print(
                    f"OUT-OF-RANGE COORDINATES: "
                    f"{label_file.name}:{line_no}"
                )
                bad_coords += 1
                continue

            objects[cls] += 1


print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)

print("Total images :", total_images)
print("Total labels :", total_labels)
print("Empty labels :", empty_labels)

print()
for cls, name in CLASS_NAMES.items():
    print(f"{name:15}: {objects[cls]}")

print("Total objects :", sum(objects.values()))

print()
print("Bad lines     :", bad_lines)
print("Bad classes   :", bad_class)
print("Bad coords    :", bad_coords)

print("=" * 60)

if (
    total_images == total_labels
    and bad_lines == 0
    and bad_class == 0
    and bad_coords == 0
):
    print("RESULT: DATASET V4 IS VALID")
else:
    print("RESULT: DATASET V4 HAS ERRORS")