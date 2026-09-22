from pathlib import Path
import random
import cv2

DATASET_DIR = Path(r"D:\AI_KLTN\dataset_seg")
OUTPUT_DIR = Path(r"D:\AI_KLTN\runs\visualize_seg")

NUM_IMAGES = 20

CLASS_NAMES = [
    "Answer_paper",
    "Cheat_Paper",
    "cellphone",
    "earphone",
    "smartwatch"
]

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

image_dir = DATASET_DIR / "train" / "images"
label_dir = DATASET_DIR / "train" / "labels"

images = list(image_dir.glob("*.jpg"))
images += list(image_dir.glob("*.jpeg"))
images += list(image_dir.glob("*.png"))

random.seed(42)
selected = random.sample(images, min(NUM_IMAGES, len(images)))

print("=" * 60)
print(" KIỂM TRA TRỰC QUAN POLYGON SEGMENTATION")
print("=" * 60)
print(f"Dataset : {DATASET_DIR}")
print(f"Số ảnh kiểm tra: {len(selected)}")
print(f"Kết quả: {OUTPUT_DIR}")
print()

for idx, image_path in enumerate(selected, 1):

    image = cv2.imread(str(image_path))

    if image is None:
        print(f"[ERROR] Không đọc được: {image_path.name}")
        continue

    h, w = image.shape[:2]

    label_path = label_dir / f"{image_path.stem}.txt"

    if not label_path.exists():
        print(f"[WARNING] Không có label: {image_path.name}")
        continue

    with open(label_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    polygon_count = 0

    for line in lines:

        parts = line.split()

        if len(parts) < 7:
            print(
                f"[WARNING] Annotation không phải polygon: "
                f"{image_path.name}"
            )
            continue

        class_id = int(parts[0])
        coords = list(map(float, parts[1:]))

        if len(coords) % 2 != 0:
            print(
                f"[ERROR] Số tọa độ không hợp lệ: "
                f"{image_path.name}"
            )
            continue

        points = []

        for i in range(0, len(coords), 2):

            x = int(coords[i] * w)
            y = int(coords[i + 1] * h)

            points.append([x, y])

        points = cv2.UMat(
            __import__("numpy").array(points, dtype="int32")
        )

        cv2.polylines(
            image,
            [points.get()],
            isClosed=True,
            color=(0, 255, 0),
            thickness=2
        )

        # Tính vị trí để ghi class
        pts = points.get()

        x_text = int(pts[:, 0].min())
        y_text = int(pts[:, 1].min()) - 5

        if y_text < 15:
            y_text = 15

        class_name = (
            CLASS_NAMES[class_id]
            if 0 <= class_id < len(CLASS_NAMES)
            else f"class_{class_id}"
        )

        cv2.putText(
            image,
            class_name,
            (x_text, y_text),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2
        )

        polygon_count += 1

    output_path = OUTPUT_DIR / image_path.name
    cv2.imwrite(str(output_path), image)

    print(
        f"[{idx:02d}/{len(selected)}] "
        f"{image_path.name} -> {polygon_count} polygon"
    )

print()
print("=" * 60)
print(" HOÀN TẤT")
print("=" * 60)
print(f"Mở thư mục:")
print(OUTPUT_DIR)