"""Gộp dataset_seg và realworld_data thành dataset_seg_v4 với 3 nhãn seg.
Luồng chính: lọc nhãn hợp lệ → chép ảnh và nhãn theo từng phần → gộp ảnh thực tế → ghi data.yaml."""

import argparse
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRAIN_DIR = PROJECT_ROOT / "training"
SOURCE_DATASET = TRAIN_DIR / "dataset_seg"
REALWORLD_DATA = TRAIN_DIR / "realworld_data"
OUTPUT_DATASET = TRAIN_DIR / "dataset_seg_v4"

VALID_CLASSES = {0, 1, 2}  # Ba nhãn giữ lại: Answer_paper, Cheat_Paper, cellphone
CLASS_NAMES = ["Answer_paper", "Cheat_Paper", "cellphone"]
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def _filter_lines(label_path: Path) -> tuple[list[str], int]:
    """Lọc giữ ba nhãn hợp lệ trong một file nhãn.
    Điểm logic: nhãn ngoài 0, 1, 2 như tai nghe hay đồng hồ thì loại bỏ."""
    kept, removed = [], 0
    if not label_path.exists():
        return kept, removed
    for line in label_path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if not parts:
            continue
        try:
            cls = int(parts[0])
        except ValueError:
            removed += 1
            continue
        if cls in VALID_CLASSES:
            kept.append(line)
        else:
            removed += 1  # Loại nhãn lạ như tai nghe hay đồng hồ
    return kept, removed


def process_split(split: str) -> None:
    """Chép ảnh và lọc nhãn của một phần train, valid hoặc test.
    Điểm logic: chỉ nhận file ảnh đúng đuôi; nhãn thiếu thì ghi file rỗng."""
    src_images = SOURCE_DATASET / split / "images"
    src_labels = SOURCE_DATASET / split / "labels"
    dst_images = OUTPUT_DATASET / split / "images"
    dst_labels = OUTPUT_DATASET / split / "labels"
    dst_images.mkdir(parents=True, exist_ok=True)
    dst_labels.mkdir(parents=True, exist_ok=True)
    if not src_images.exists():
        print(f"[{split}] thiếu {src_images} -> skip")
        return
    n_img = n_obj = n_rm = 0
    for img in src_images.iterdir():
        if not img.is_file() or img.suffix.lower() not in IMAGE_EXTS:
            continue
        shutil.copy2(img, dst_images / img.name)
        n_img += 1
        kept, removed = _filter_lines(src_labels / f"{img.stem}.txt")
        (dst_labels / f"{img.stem}.txt").write_text("\n".join(kept), encoding="utf-8")
        n_obj += len(kept)
        n_rm += removed
    print(f"[{split}] images={n_img} kept={n_obj} removed={n_rm}")


def add_realworld() -> None:
    """Gộp ảnh thực tế vào tập train với tiền tố rw_ chống trùng tên.
    Điểm logic: lọc nhãn lại như tập chính rồi mới chép và ghi nhãn."""
    src_images = REALWORLD_DATA / "train" / "images"
    src_labels = REALWORLD_DATA / "train" / "labels"
    if not src_images.exists():
        print("[realworld] thiếu train/images -> skip")
        return
    dst_images = OUTPUT_DATASET / "train" / "images"
    dst_labels = OUTPUT_DATASET / "train" / "labels"
    n = 0
    for img in src_images.iterdir():
        if not img.is_file() or img.suffix.lower() not in IMAGE_EXTS:
            continue
        kept, _ = _filter_lines(src_labels / f"{img.stem}.txt")
        (shutil.copy2(img, dst_images / f"rw_{img.name}"), n := n + 1)
        (dst_labels / f"rw_{img.stem}.txt").write_text("\n".join(kept), encoding="utf-8")
    print(f"[realworld] images={n} (prefix rw_)")


def main() -> int:
    """Chạy toàn bộ gộp dataset cho ba phần rồi ghi data.yaml 3 nhãn.
    Điểm logic: cờ --clean xóa dataset cũ trước khi gộp lại từ đầu."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--clean", action="store_true", help="Xoá dataset_seg_v4 cũ trước")
    args = ap.parse_args()
    if args.clean and OUTPUT_DATASET.exists():
        shutil.rmtree(OUTPUT_DATASET)
        print(f"Đã xoá {OUTPUT_DATASET}")
    for split in ("train", "valid", "test"):
        process_split(split)
    add_realworld()
    (OUTPUT_DATASET / "data.yaml").write_text(
        "train: train/images\nval: valid/images\ntest: test/images\n\nnc: 3\nnames:\n"
        "- Answer_paper\n- Cheat_Paper\n- cellphone\n",
        encoding="utf-8",
    )
    print(f"Xong: {OUTPUT_DATASET} | classes={CLASS_NAMES}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
