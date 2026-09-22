from pathlib import Path
from collections import Counter


# ============================================================
# CẤU HÌNH
# ============================================================

DATASET_DIR = Path(r"D:\AI_KLTN\dataset")

SPLITS = {
    "train": DATASET_DIR / "train" / "labels",
    "valid": DATASET_DIR / "valid" / "labels",
    "test": DATASET_DIR / "test" / "labels",
}

NUM_CLASSES = 5


# ============================================================
# KIỂM TRA MỘT DÒNG ANNOTATION
# ============================================================

def classify_line(line):
    """
    Phân loại một dòng annotation YOLO:

    Detection:
        class x_center y_center width height
        -> 5 giá trị

    Segmentation:
        class x1 y1 x2 y2 x3 y3 ...
        -> từ 7 giá trị trở lên và số tọa độ là số chẵn

    Invalid:
        Không đúng định dạng.
    """

    parts = line.strip().split()

    if not parts:
        return "empty"

    # Kiểm tra class ID
    try:
        class_id = int(parts[0])
    except ValueError:
        return "invalid"

    if class_id < 0 or class_id >= NUM_CLASSES:
        return "invalid"

    # Detection YOLO
    if len(parts) == 5:
        try:
            coords = [float(x) for x in parts[1:]]

            if all(0 <= x <= 1 for x in coords):
                return "detection"

            return "invalid"

        except ValueError:
            return "invalid"

    # Segmentation YOLO
    if len(parts) >= 7 and (len(parts) - 1) % 2 == 0:
        try:
            coords = [float(x) for x in parts[1:]]

            if all(0 <= x <= 1 for x in coords):
                return "segmentation"

            return "invalid"

        except ValueError:
            return "invalid"

    return "invalid"


# ============================================================
# KIỂM TRA MỘT FILE
# ============================================================

def analyze_file(label_file):
    types = []
    total_lines = 0

    with open(label_file, "r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):

            if not line.strip():
                continue

            total_lines += 1

            result = classify_line(line)

            types.append((result, line_number, line.strip()))

    if total_lines == 0:
        return "empty", types

    type_counter = Counter(x[0] for x in types)

    has_detection = type_counter["detection"] > 0
    has_segmentation = type_counter["segmentation"] > 0
    has_invalid = type_counter["invalid"] > 0

    # Có cả detection và segmentation
    if has_detection and has_segmentation:
        file_type = "mixed"

    # Có annotation không hợp lệ
    elif has_invalid:
        file_type = "invalid"

    # Chỉ detection
    elif has_detection:
        file_type = "detection_only"

    # Chỉ segmentation
    elif has_segmentation:
        file_type = "segmentation_only"

    else:
        file_type = "empty"

    return file_type, types


# ============================================================
# PHÂN TÍCH TỪNG SPLIT
# ============================================================

def analyze_split(split_name, label_dir):

    print()
    print("=" * 75)
    print(f" SPLIT: {split_name.upper()}")
    print("=" * 75)

    if not label_dir.exists():
        print(f"[WARNING] Không tìm thấy thư mục: {label_dir}")
        return

    label_files = sorted(label_dir.glob("*.txt"))

    print(f"Số file annotation: {len(label_files)}")

    file_counter = Counter()

    total_detection_rows = 0
    total_segmentation_rows = 0
    total_invalid_rows = 0

    mixed_files = []
    invalid_files = []
    segmentation_only_files = []

    for label_file in label_files:

        file_type, details = analyze_file(label_file)

        file_counter[file_type] += 1

        for row_type, _, _ in details:

            if row_type == "detection":
                total_detection_rows += 1

            elif row_type == "segmentation":
                total_segmentation_rows += 1

            elif row_type == "invalid":
                total_invalid_rows += 1

        if file_type == "mixed":
            mixed_files.append(label_file)

        elif file_type == "invalid":
            invalid_files.append(label_file)

        elif file_type == "segmentation_only":
            segmentation_only_files.append(label_file)

    # --------------------------------------------------------
    # THỐNG KÊ
    # --------------------------------------------------------

    print()
    print("PHÂN LOẠI FILE:")
    print(f"  Detection only     : {file_counter['detection_only']}")
    print(f"  Segmentation only  : {file_counter['segmentation_only']}")
    print(f"  Mixed              : {file_counter['mixed']}")
    print(f"  Invalid            : {file_counter['invalid']}")
    print(f"  Empty              : {file_counter['empty']}")

    print()
    print("THỐNG KÊ DÒNG ANNOTATION:")
    print(f"  Detection rows     : {total_detection_rows}")
    print(f"  Segmentation rows  : {total_segmentation_rows}")
    print(f"  Invalid rows       : {total_invalid_rows}")

    # --------------------------------------------------------
    # FILE MIXED
    # --------------------------------------------------------

    if mixed_files:

        print()
        print("-" * 75)
        print(f"FILE MIXED ({len(mixed_files)} FILE)")
        print("-" * 75)

        for f in mixed_files:
            print(f"  {f.name}")

    # --------------------------------------------------------
    # FILE INVALID
    # --------------------------------------------------------

    if invalid_files:

        print()
        print("-" * 75)
        print(f"FILE INVALID ({len(invalid_files)} FILE)")
        print("-" * 75)

        for f in invalid_files:
            print(f"  {f.name}")

    # --------------------------------------------------------
    # FILE SEGMENTATION ONLY
    # --------------------------------------------------------

    if segmentation_only_files:

        print()
        print("-" * 75)
        print(
            f"FILE SEGMENTATION ONLY ({len(segmentation_only_files)} FILE)"
        )
        print("-" * 75)

        for f in segmentation_only_files:
            print(f"  {f.name}")


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 75)
    print(" KIỂM TRA KIỂU ANNOTATION DATASET EXAM_MONITOR")
    print("=" * 75)

    print(f"Dataset: {DATASET_DIR}")

    for split_name, label_dir in SPLITS.items():
        analyze_split(split_name, label_dir)

    print()
    print("=" * 75)
    print(" HOÀN TẤT KIỂM TRA")
    print("=" * 75)


if __name__ == "__main__":
    main()