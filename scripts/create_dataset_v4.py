from pathlib import Path
import shutil

# =========================
# PATHS
# =========================
BASE = Path(r"D:\AI_KLTN")

SOURCE_DATASET = BASE / "dataset_seg"
REALWORLD_DATA = BASE / "realworld_data"
OUTPUT_DATASET = BASE / "dataset_seg_v4"

# =========================
# SETTINGS
# =========================
VALID_CLASSES = {
    0: 0,  # Answer_paper
    1: 1,  # Cheat_Paper
    2: 2,  # cellphone
}

CLASS_NAMES = [
    "Answer_paper",
    "Cheat_Paper",
    "cellphone",
]

# =========================
# CLEAN OLD OUTPUT
# =========================
if OUTPUT_DATASET.exists():
    print(f"Removing old dataset: {OUTPUT_DATASET}")
    shutil.rmtree(OUTPUT_DATASET)

# Create structure
for split in ["train", "valid", "test"]:
    (OUTPUT_DATASET / split / "images").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DATASET / split / "labels").mkdir(parents=True, exist_ok=True)


# =========================
# COPY + FILTER ORIGINAL DATASET
# =========================
def process_original_split(split):
    src_images = SOURCE_DATASET / split / "images"
    src_labels = SOURCE_DATASET / split / "labels"

    dst_images = OUTPUT_DATASET / split / "images"
    dst_labels = OUTPUT_DATASET / split / "labels"

    if not src_images.exists():
        print(f"[{split}] source images not found -> skip")
        return

    if not src_labels.exists():
        print(f"[{split}] source labels not found -> skip")
        return

    image_count = 0
    label_count = 0
    object_count = 0
    removed_objects = 0

    image_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

    for image in src_images.iterdir():
        if not image.is_file() or image.suffix.lower() not in image_exts:
            continue

        label = src_labels / f"{image.stem}.txt"

        # Copy image
        shutil.copy2(image, dst_images / image.name)
        image_count += 1

        # If no label exists, create empty label
        if not label.exists():
            (dst_labels / label.name).write_text("", encoding="utf-8")
            label_count += 1
            continue

        new_lines = []

        for line in label.read_text(encoding="utf-8").splitlines():
            parts = line.split()

            if not parts:
                continue

            try:
                cls = int(parts[0])
            except ValueError:
                print(f"WARNING: invalid label: {label}")
                continue

            if cls in VALID_CLASSES:
                # Keep original class ID because 0,1,2 remain unchanged
                new_lines.append(line)
                object_count += 1
            else:
                # Remove earphone / smartwatch
                removed_objects += 1

        (dst_labels / label.name).write_text(
            "\n".join(new_lines),
            encoding="utf-8"
        )

        label_count += 1

    print(
        f"[{split}] images={image_count}, "
        f"labels={label_count}, "
        f"objects_kept={object_count}, "
        f"objects_removed={removed_objects}"
    )


process_original_split("train")
process_original_split("valid")
process_original_split("test")


# =========================
# ADD REALWORLD TRAIN DATA
# =========================
src_images = REALWORLD_DATA / "train" / "images"
src_labels = REALWORLD_DATA / "train" / "labels"

dst_images = OUTPUT_DATASET / "train" / "images"
dst_labels = OUTPUT_DATASET / "train" / "labels"

realworld_images = 0
realworld_labels = 0
realworld_objects = 0

image_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

for image in src_images.iterdir():
    if not image.is_file() or image.suffix.lower() not in image_exts:
        continue

    label = src_labels / f"{image.stem}.txt"

    # Prefix prevents filename collisions
    new_name = f"rw_{image.name}"
    new_label_name = f"rw_{image.stem}.txt"

    shutil.copy2(image, dst_images / new_name)

    if label.exists():
        lines = label.read_text(encoding="utf-8").splitlines()

        valid_lines = []

        for line in lines:
            parts = line.split()

            if not parts:
                continue

            try:
                cls = int(parts[0])
            except ValueError:
                continue

            if cls in VALID_CLASSES:
                valid_lines.append(line)
                realworld_objects += 1

        (dst_labels / new_label_name).write_text(
            "\n".join(valid_lines),
            encoding="utf-8"
        )
    else:
        (dst_labels / new_label_name).write_text(
            "",
            encoding="utf-8"
        )

    realworld_images += 1
    realworld_labels += 1


print(
    f"[realworld] images={realworld_images}, "
    f"labels={realworld_labels}, "
    f"objects={realworld_objects}"
)


# =========================
# CREATE DATA.YAML
# =========================
yaml_content = """train: train/images
val: valid/images
test: test/images

nc: 3
names:
- Answer_paper
- Cheat_Paper
- cellphone
"""

(OUTPUT_DATASET / "data.yaml").write_text(
    yaml_content,
    encoding="utf-8"
)


# =========================
# SUMMARY
# =========================
print()
print("=" * 60)
print("DATASET V4 CREATED SUCCESSFULLY")
print("=" * 60)
print(f"Output: {OUTPUT_DATASET}")
print()
print("Classes:")
for i, name in enumerate(CLASS_NAMES):
    print(f"  {i}: {name}")

print()
print("Realworld data added:")
print(f"  Images : {realworld_images}")
print(f"  Labels : {realworld_labels}")
print(f"  Objects: {realworld_objects}")

print()
print("IMPORTANT:")
print("- Original dataset_seg was NOT modified.")
print("- realworld_data was NOT modified.")
print("- Realworld filenames were prefixed with 'rw_'.")
print("- earphone and smartwatch objects were removed.")
print("=" * 60)