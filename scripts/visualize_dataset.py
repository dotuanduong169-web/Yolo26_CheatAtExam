import os
import random
import cv2

# =========================
# CẤU HÌNH
# =========================

IMAGE_DIR = r"D:\AI_KLTN\dataset\train\images"
LABEL_DIR = r"D:\AI_KLTN\dataset\train\labels"
OUTPUT_DIR = r"D:\AI_KLTN\dataset_preview"

CLASS_NAMES = [
    "Answer_paper",
    "Cheat_Paper",
    "cellphone",
    "earphone",
    "smartwatch"
]

NUM_IMAGES = 20
RANDOM_SEED = 42


# =========================
# TẠO THƯ MỤC OUTPUT
# =========================

os.makedirs(OUTPUT_DIR, exist_ok=True)

random.seed(RANDOM_SEED)


# =========================
# LẤY DANH SÁCH ẢNH
# =========================

valid_extensions = (".jpg", ".jpeg", ".png", ".bmp", ".webp")

image_files = [
    f for f in os.listdir(IMAGE_DIR)
    if f.lower().endswith(valid_extensions)
]

if not image_files:
    print("KHONG TIM THAY ANH TRONG:", IMAGE_DIR)
    exit()

print(f"Tim thay {len(image_files)} anh.")


# =========================
# CHỌN ẢNH NGẪU NHIÊN
# =========================

sample_count = min(NUM_IMAGES, len(image_files))

selected_images = random.sample(image_files, sample_count)

print(f"Dang kiem tra {sample_count} anh...")


# =========================
# KIỂM TRA VÀ VẼ BOUNDING BOX
# =========================

error_count = 0

for index, image_name in enumerate(selected_images, start=1):

    image_path = os.path.join(IMAGE_DIR, image_name)

    # Tên file label tương ứng
    base_name = os.path.splitext(image_name)[0]
    label_name = base_name + ".txt"
    label_path = os.path.join(LABEL_DIR, label_name)

    # Đọc ảnh
    image = cv2.imread(image_path)

    if image is None:
        print(f"[LOI] Khong doc duoc anh: {image_name}")
        error_count += 1
        continue

    height, width = image.shape[:2]

    # Kiểm tra label
    if not os.path.exists(label_path):
        print(f"[LOI] Khong co label cho: {image_name}")
        error_count += 1
        continue

    with open(label_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    # Đọc từng object
    for line_number, line in enumerate(lines, start=1):

        parts = line.split()

        if len(parts) != 5:
            print(
                f"[LOI] {label_name}, dong {line_number}: "
                f"khong dung 5 gia tri"
            )
            error_count += 1
            continue

        try:
            class_id = int(parts[0])
            x_center = float(parts[1])
            y_center = float(parts[2])
            box_width = float(parts[3])
            box_height = float(parts[4])

        except ValueError:
            print(
                f"[LOI] {label_name}, dong {line_number}: "
                f"gia tri khong hop le"
            )
            error_count += 1
            continue

        # Kiểm tra class ID
        if class_id < 0 or class_id >= len(CLASS_NAMES):
            print(
                f"[LOI] {label_name}, dong {line_number}: "
                f"class ID = {class_id} khong hop le"
            )
            error_count += 1
            continue

        # Kiểm tra tọa độ YOLO
        values = [
            x_center,
            y_center,
            box_width,
            box_height
        ]

        if any(v < 0 or v > 1 for v in values):
            print(
                f"[LOI] {label_name}, dong {line_number}: "
                f"toa do nam ngoai khoang 0-1"
            )
            error_count += 1
            continue

        # Chuyển YOLO normalized -> pixel
        x1 = int((x_center - box_width / 2) * width)
        y1 = int((y_center - box_height / 2) * height)
        x2 = int((x_center + box_width / 2) * width)
        y2 = int((y_center + box_height / 2) * height)

        # Giới hạn trong ảnh
        x1 = max(0, min(x1, width - 1))
        y1 = max(0, min(y1, height - 1))
        x2 = max(0, min(x2, width - 1))
        y2 = max(0, min(y2, height - 1))

        # Tên class
        class_name = CLASS_NAMES[class_id]

        label_text = f"{class_name}"

        # Vẽ bounding box
        cv2.rectangle(
            image,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            2
        )

        # Kích thước text
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness = 2

        (text_width, text_height), baseline = cv2.getTextSize(
            label_text,
            font,
            font_scale,
            thickness
        )

        # Vị trí nền của label
        label_y1 = max(0, y1 - text_height - baseline - 5)
        label_y2 = y1

        cv2.rectangle(
            image,
            (x1, label_y1),
            (x1 + text_width + 5, label_y2),
            (0, 255, 0),
            -1
        )

        # Vẽ tên class
        cv2.putText(
            image,
            label_text,
            (x1 + 2, max(text_height, y1 - 5)),
            font,
            font_scale,
            (0, 0, 0),
            thickness,
            cv2.LINE_AA
        )

    # =========================
    # LƯU ẢNH PREVIEW
    # =========================

    output_name = f"{index:02d}_{image_name}"
    output_path = os.path.join(OUTPUT_DIR, output_name)

    cv2.imwrite(output_path, image)

    print(f"[OK] {output_name}")


# =========================
# KẾT QUẢ
# =========================

print()
print("=" * 50)
print("HOAN THANH KIEM TRA")
print("=" * 50)

print(f"Anh da kiem tra : {sample_count}")
print(f"So loi phat hien: {error_count}")
print(f"Ket qua luu tai : {OUTPUT_DIR}")

if error_count == 0:
    print()
    print("Khong phat hien loi ve cau truc annotation.")
else:
    print()
    print("Co annotation can kiem tra lai.")