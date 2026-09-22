from pathlib import Path

# ============================================================
# CẤU HÌNH
# ============================================================

DATASET_DIR = Path(r"D:\AI_KLTN\dataset_seg")

SPLITS = {
    "TRAIN": DATASET_DIR / "train" / "labels",
    "VALID": DATASET_DIR / "valid" / "labels",
    "TEST": DATASET_DIR / "test" / "labels",
}

CLASS_COUNT = 5


# ============================================================
# KIỂM TRA MỘT DÒNG ANNOTATION
# ============================================================

def classify_line(line):
    parts = line.strip().split()

    if not parts:
        return "empty"

    # --------------------------------------------------------
    # YOLO Detection:
    # class x_center y_center width height
    # => đúng 5 giá trị
    # --------------------------------------------------------
    if len(parts) == 5:
        try:
            class_id = int(float(parts[0]))
            coords = [float(x) for x in parts[1:]]

            if not (0 <= class_id < CLASS_COUNT):
                return "invalid"

            if not all(0 <= x <= 1 for x in coords):
                return "invalid"

            return "detection"

        except ValueError:
            return "invalid"

    # --------------------------------------------------------
    # YOLO Segmentation:
    # class x1 y1 x2 y2 x3 y3 ...
    # => ít nhất 7 giá trị
    # => sau class phải là các cặp tọa độ
    # --------------------------------------------------------
    if len(parts) >= 7 and (len(parts) - 1) % 2 == 0:
        try:
            class_id = int(float(parts[0]))
            coords = [float(x) for x in parts[1:]]

            if not (0 <= class_id < CLASS_COUNT):
                return "invalid"

            if not all(0 <= x <= 1 for x in coords):
                return "invalid"

            return "segmentation"

        except ValueError:
            return "invalid"

    return "invalid"


# ============================================================
# KIỂM TRA MỘT SPLIT
# ============================================================

def check_split(split_name, label_dir):

    print()
    print("=" * 60)
    print(f" {split_name}")
    print("=" * 60)

    if not label_dir.exists():
        print(f"KHÔNG TÌM THẤY THƯ MỤC: {label_dir}")
        return

    label_files = list(label_dir.glob("*.txt"))

    detection_only = 0
    segmentation_only = 0
    mixed = 0
    invalid_files = 0
    empty_files = 0

    detection_rows = 0
    segmentation_rows = 0
    invalid_rows = 0

    for label_file in label_files:

        file_types = set()

        try:
            with open(label_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

        except Exception:
            invalid_files += 1
            continue

        has_content = False

        for line in lines:

            if not line.strip():
                continue

            has_content = True

            result = classify_line(line)

            if result == "detection":
                detection_rows += 1
                file_types.add("detection")

            elif result == "segmentation":
                segmentation_rows += 1
                file_types.add("segmentation")

            elif result == "invalid":
                invalid_rows += 1

        # ----------------------------------------------------
        # Phân loại file
        # ----------------------------------------------------

        if not has_content:
            empty_files += 1

        elif invalid_rows > 0 and not file_types:
            invalid_files += 1

        elif "detection" in file_types and "segmentation" in file_types:
            mixed += 1

        elif "detection" in file_types:
            detection_only += 1

        elif "segmentation" in file_types:
            segmentation_only += 1

        else:
            invalid_files += 1

    # --------------------------------------------------------
    # IN KẾT QUẢ
    # --------------------------------------------------------

    print(f"Tổng file annotation : {len(label_files)}")
    print()

    print("PHÂN LOẠI FILE:")
    print(f"  Detection only     : {detection_only}")
    print(f"  Segmentation only  : {segmentation_only}")
    print(f"  Mixed              : {mixed}")
    print(f"  Invalid            : {invalid_files}")
    print(f"  Empty              : {empty_files}")

    print()

    print("THỐNG KÊ DÒNG ANNOTATION:")
    print(f"  Detection rows     : {detection_rows}")
    print(f"  Segmentation rows  : {segmentation_rows}")
    print(f"  Invalid rows       : {invalid_rows}")


# ============================================================
# MAIN
# ============================================================

print()
print("=" * 60)
print(" KIỂM TRA TỔNG HỢP ANNOTATION DATASET")
print("=" * 60)
print(f"Dataset: {DATASET_DIR}")

for split_name, label_dir in SPLITS.items():
    check_split(split_name, label_dir)

print()
print("=" * 60)
print(" HOÀN TẤT KIỂM TRA")
print("=" * 60)
