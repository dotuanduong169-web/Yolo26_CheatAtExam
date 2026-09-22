from pathlib import Path
import shutil

# ============================================================
# CẤU HÌNH
# ============================================================

SOURCE_DIR = Path(r"D:\AI_KLTN\dataset")
OUTPUT_DIR = Path(r"D:\AI_KLTN\dataset_seg")

SPLITS = ["train", "valid", "test"]

CLASS_COUNT = 5


# ============================================================
# KIỂM TRA DETECTION
# ============================================================

def parse_detection(parts):
    """
    YOLO Detection:
    class x_center y_center width height
    """

    if len(parts) != 5:
        return None

    try:
        class_id = int(float(parts[0]))
        x_center = float(parts[1])
        y_center = float(parts[2])
        width = float(parts[3])
        height = float(parts[4])
    except ValueError:
        return None

    if not (0 <= class_id < CLASS_COUNT):
        return None

    values = [x_center, y_center, width, height]

    if not all(0 <= x <= 1 for x in values):
        return None

    if width <= 0 or height <= 0:
        return None

    return class_id, x_center, y_center, width, height


# ============================================================
# CHUYỂN BOUNDING BOX → POLYGON
# ============================================================

def detection_to_polygon(class_id, xc, yc, w, h):

    xmin = xc - w / 2
    ymin = yc - h / 2
    xmax = xc + w / 2
    ymax = yc + h / 2

    # Giới hạn trong [0, 1]
    xmin = max(0.0, min(1.0, xmin))
    ymin = max(0.0, min(1.0, ymin))
    xmax = max(0.0, min(1.0, xmax))
    ymax = max(0.0, min(1.0, ymax))

    # Polygon hình chữ nhật
    return (
        f"{class_id} "
        f"{xmin:.6f} {ymin:.6f} "
        f"{xmax:.6f} {ymin:.6f} "
        f"{xmax:.6f} {ymax:.6f} "
        f"{xmin:.6f} {ymax:.6f}"
    )


# ============================================================
# XỬ LÝ MỘT FILE
# ============================================================

def convert_label_file(source_file, output_file):

    converted_lines = []

    with open(source_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:

        line = line.strip()

        if not line:
            continue

        parts = line.split()

        # ----------------------------------------------------
        # Trường hợp 1:
        # Annotation đã là segmentation
        # ----------------------------------------------------

        if len(parts) >= 7 and (len(parts) - 1) % 2 == 0:

            try:
                class_id = int(float(parts[0]))
                coords = [float(x) for x in parts[1:]]

                if (
                    0 <= class_id < CLASS_COUNT
                    and all(0 <= x <= 1 for x in coords)
                ):
                    converted_lines.append(line)
                    continue

            except ValueError:
                pass

        # ----------------------------------------------------
        # Trường hợp 2:
        # Annotation là detection
        # → chuyển thành polygon hình chữ nhật
        # ----------------------------------------------------

        detection = parse_detection(parts)

        if detection is not None:

            class_id, xc, yc, w, h = detection

            polygon = detection_to_polygon(
                class_id,
                xc,
                yc,
                w,
                h
            )

            converted_lines.append(polygon)

            continue

        # ----------------------------------------------------
        # Nếu không nhận dạng được
        # ----------------------------------------------------

        raise ValueError(
            f"Annotation không hợp lệ trong file:\n"
            f"{source_file}\n"
            f"Dòng: {line}"
        )

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(converted_lines))

        if converted_lines:
            f.write("\n")


# ============================================================
# COPY DATASET
# ============================================================

def process_split(split):

    source_images = SOURCE_DIR / split / "images"
    source_labels = SOURCE_DIR / split / "labels"

    output_images = OUTPUT_DIR / split / "images"
    output_labels = OUTPUT_DIR / split / "labels"

    output_images.mkdir(
        parents=True,
        exist_ok=True
    )

    output_labels.mkdir(
        parents=True,
        exist_ok=True
    )

    if not source_images.exists():
        print(f"[WARNING] Không tìm thấy: {source_images}")
        return

    if not source_labels.exists():
        print(f"[WARNING] Không tìm thấy: {source_labels}")
        return

    image_files = list(source_images.glob("*"))

    converted = 0
    errors = 0

    for image_file in image_files:

        # ----------------------------------------------------
        # Copy image
        # ----------------------------------------------------

        output_image = output_images / image_file.name

        shutil.copy2(
            image_file,
            output_image
        )

        # ----------------------------------------------------
        # Tìm annotation tương ứng
        # ----------------------------------------------------

        label_file = source_labels / f"{image_file.stem}.txt"

        if not label_file.exists():

            print(
                f"[WARNING] Không có annotation: "
                f"{image_file.name}"
            )

            continue

        output_label = output_labels / label_file.name

        # ----------------------------------------------------
        # Convert
        # ----------------------------------------------------

        try:

            convert_label_file(
                label_file,
                output_label
            )

            converted += 1

        except Exception as e:

            errors += 1

            print()
            print("[ERROR]")
            print(e)
            print()

    print()
    print(f"{split.upper()}:")
    print(f"  Images      : {len(image_files)}")
    print(f"  Converted   : {converted}")
    print(f"  Errors      : {errors}")


# ============================================================
# MAIN
# ============================================================

print("=" * 60)
print(" CHUYỂN DATASET → YOLO26 INSTANCE SEGMENTATION")
print("=" * 60)

print()
print(f"Dataset gốc : {SOURCE_DIR}")
print(f"Dataset mới : {OUTPUT_DIR}")

# Không ghi đè dataset gốc
if OUTPUT_DIR.exists():

    print()
    print("[ERROR]")
    print("Thư mục dataset_seg đã tồn tại.")
    print("Hãy xóa hoặc đổi tên thư mục này trước khi chạy lại.")

    raise SystemExit(1)

# ------------------------------------------------------------
# Xử lý từng split
# ------------------------------------------------------------

for split in SPLITS:

    process_split(split)

# ------------------------------------------------------------
# Copy data.yaml
# ------------------------------------------------------------

source_yaml = SOURCE_DIR / "data.yaml"
output_yaml = OUTPUT_DIR / "data.yaml"

if source_yaml.exists():

    shutil.copy2(
        source_yaml,
        output_yaml
    )

    print()
    print("Đã copy data.yaml")

print()
print("=" * 60)
print(" HOÀN TẤT")
print("=" * 60)

print()
print("Dataset mới:")
print(OUTPUT_DIR)

print()
print("Bước tiếp theo:")
print("Kiểm tra lại annotation trước khi train.")