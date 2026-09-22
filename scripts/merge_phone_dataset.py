from pathlib import Path
import shutil
import yaml

# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(r"D:\AI_KLTN")

OLD_DATASET = BASE_DIR / "dataset_seg"
NEW_DATASET = BASE_DIR / "more_data"
OUTPUT_DATASET = BASE_DIR / "dataset_seg_v2"

# ============================================================
# CLASS MAPPING
# ============================================================

# Dataset cũ:
# 0 Answer_paper
# 1 Cheat_Paper
# 2 cellphone
# 3 earphone
# 4 smartwatch

# Dataset mới:
# 0 phone
#
# phone -> cellphone = class 2
NEW_CLASS_ID = 2

CLASS_NAMES = [
    "Answer_paper",
    "Cheat_Paper",
    "cellphone",
    "earphone",
    "smartwatch",
]


# ============================================================
# FUNCTIONS
# ============================================================

def convert_detection_to_polygon(line):
    """
    Convert YOLO detection:
        class xc yc w h

    to YOLO segmentation rectangle:
        class x1 y1 x2 y2 x3 y3 x4 y4
    """

    parts = line.strip().split()

    if len(parts) != 5:
        raise ValueError(
            f"Expected 5 values for detection label, got {len(parts)}: {line}"
        )

    _, xc, yc, w, h = parts

    xc = float(xc)
    yc = float(yc)
    w = float(w)
    h = float(h)

    x1 = xc - w / 2
    y1 = yc - h / 2
    x2 = xc + w / 2
    y2 = yc - h / 2
    x3 = xc + w / 2
    y3 = yc + h / 2
    x4 = xc - w / 2
    y4 = yc + h / 2

    # Clamp coordinates to [0, 1]
    coords = [
        max(0.0, min(1.0, x1)),
        max(0.0, min(1.0, y1)),
        max(0.0, min(1.0, x2)),
        max(0.0, min(1.0, y2)),
        max(0.0, min(1.0, x3)),
        max(0.0, min(1.0, y3)),
        max(0.0, min(1.0, x4)),
        max(0.0, min(1.0, y4)),
    ]

    return f"{NEW_CLASS_ID} " + " ".join(f"{v:.6f}" for v in coords)


def copy_old_dataset(split):
    """
    Copy existing segmentation dataset without modifying labels.
    """

    src_images = OLD_DATASET / split / "images"
    src_labels = OLD_DATASET / split / "labels"

    dst_images = OUTPUT_DATASET / split / "images"
    dst_labels = OUTPUT_DATASET / split / "labels"

    image_count = 0
    label_count = 0

    for image in src_images.iterdir():
        if image.is_file():
            shutil.copy2(image, dst_images / image.name)
            image_count += 1

    for label in src_labels.iterdir():
        if label.is_file():
            shutil.copy2(label, dst_labels / label.name)
            label_count += 1

    print(f"[OLD] {split}: {image_count} images, {label_count} labels")


def process_new_phone_dataset(split):
    """
    Copy phone images and convert their YOLO detection labels
    into segmentation labels with class ID 2 (cellphone).
    """

    src_images = NEW_DATASET / split / "images"
    src_labels = NEW_DATASET / split / "labels"

    dst_images = OUTPUT_DATASET / split / "images"
    dst_labels = OUTPUT_DATASET / split / "labels"

    image_count = 0
    label_count = 0
    object_count = 0

    valid_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

    for image in src_images.iterdir():

        if not image.is_file():
            continue

        if image.suffix.lower() not in valid_extensions:
            continue

        label = src_labels / f"{image.stem}.txt"

        if not label.exists():
            print(f"[WARNING] Missing label: {label}")
            continue

        # Copy image
        shutil.copy2(image, dst_images / image.name)
        image_count += 1

        # Convert labels
        converted_lines = []

        with open(label, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()

                if not line:
                    continue

                converted = convert_detection_to_polygon(line)
                converted_lines.append(converted)
                object_count += 1

        # Write converted segmentation label
        output_label = dst_labels / label.name

        with open(output_label, "w", encoding="utf-8") as f:
            f.write("\n".join(converted_lines))

        label_count += 1

    print(
        f"[NEW PHONE] {split}: "
        f"{image_count} images, "
        f"{label_count} labels, "
        f"{object_count} objects"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("CREATING dataset_seg_v2")
    print("=" * 60)

    if OUTPUT_DATASET.exists():
        raise RuntimeError(
            f"\nOutput dataset already exists:\n{OUTPUT_DATASET}\n\n"
            "Delete/rename it manually if you want to run the script again."
        )

    # Create directories
    for split in ["train", "valid"]:
        (OUTPUT_DATASET / split / "images").mkdir(
            parents=True,
            exist_ok=True
        )

        (OUTPUT_DATASET / split / "labels").mkdir(
            parents=True,
            exist_ok=True
        )

    # Copy old dataset
    print("\n--- COPYING ORIGINAL DATASET ---")

    for split in ["train", "valid"]:
        copy_old_dataset(split)

    # Add phone dataset
    print("\n--- ADDING PHONE DATASET ---")

    for split in ["train", "valid"]:
        process_new_phone_dataset(split)

    # Create data.yaml
    data_yaml = {
        "train": "train/images",
        "val": "valid/images",
        "test": "test/images",
        "nc": 5,
        "names": CLASS_NAMES,
    }

    with open(
        OUTPUT_DATASET / "data.yaml",
        "w",
        encoding="utf-8"
    ) as f:
        yaml.safe_dump(
            data_yaml,
            f,
            sort_keys=False,
            allow_unicode=True
        )

    print("\n" + "=" * 60)
    print("MERGE COMPLETED")
    print("=" * 60)
    print(f"Output: {OUTPUT_DATASET}")
    print("\nClasses:")

    for i, name in enumerate(CLASS_NAMES):
        print(f"  {i}: {name}")


if __name__ == "__main__":
    main()