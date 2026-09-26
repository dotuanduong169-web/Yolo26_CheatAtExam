"""Kiểm tra nhanh dataset YOLO-seg trước khi train.
Luồng chính: khớp ảnh-nhãn → phân bố lớp → định dạng dòng → rò rỉ train/valid → vẽ mẫu.

Ví dụ:
    python check_dataset.py
    python check_dataset.py --root ../dataset_seg_v4 --visualize 12 --out ./qa_preview
"""

import argparse
import random
from collections import Counter
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "dataset_seg_v4"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
CLASS_NAMES = ["Answer_paper", "Cheat_Paper", "cellphone"]


def classify_row(parts: list[str], n_classes: int) -> str:
    """detection = 5 giá trị; segmentation = >=7 giá trị và số tọa độ chẵn; còn lại invalid."""
    if not parts:
        return "empty"
    try:
        cls = int(float(parts[0]))
    except ValueError:
        return "invalid"
    if not (0 <= cls < n_classes):
        return "invalid"
    try:
        coords = [float(x) for x in parts[1:]]
    except ValueError:
        return "invalid"
    if len(parts) == 5 and all(0 <= v <= 1 for v in coords):
        return "detection"
    if len(parts) >= 7 and len(coords) % 2 == 0 and all(0 <= v <= 1 for v in coords):
        return "segmentation"
    return "invalid"


def check_split(root: Path, split: str, n_classes: int) -> tuple[Counter, set]:
    """Trả về (phân bố lớp, tập stem nhãn) và in báo cáo một split."""
    img_dir, lbl_dir = root / split / "images", root / split / "labels"
    imgs = {p.stem for p in img_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS} if img_dir.exists() else set()
    files = list(lbl_dir.glob("*.txt")) if lbl_dir.exists() else []
    dist, kinds = Counter(), Counter()
    bad: list[str] = []
    for f in files:
        for no, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            parts = line.split()
            if not parts:
                continue
            kind = classify_row(parts, n_classes)
            kinds[kind] += 1
            if kind in ("detection", "segmentation"):
                dist[int(float(parts[0]))] += 1
            else:
                bad.append(f"{f.name}:{no}")
    stems = {p.stem for p in files}
    print(f"[{split}] images={len(imgs)} labels={len(files)} "
          f"thieu_nhan={len(imgs - stems)} nhan_thua={len(stems - imgs)}")
    print(f"  lop: " + ", ".join(f"{CLASS_NAMES[c] if c < len(CLASS_NAMES) else c}={dist[c]}" for c in sorted(dist)))
    print(f"  dong: detection={kinds['detection']} segmentation={kinds['segmentation']} invalid={kinds['invalid']}")
    for b in bad[:10]:
        print(f"  INVALID: {b}")
    if bad:
        print(f"  ... tong {len(bad)} dong loi")
    return dist, stems


def warn_imbalance(dist: Counter) -> None:
    """Cảnh báo khi lớp ít nhất dưới 20% lớp nhiều nhất (Cheat_Paper hay đói)."""
    if len(dist) < 2:
        return
    top, low = max(dist.values()), min(dist.values())
    ratio = low / top if top else 0
    if ratio < 0.2:
        print(f"CANH BAO mat can bang: lop it nhat chi bang {ratio:.0%} lop nhieu nhat "
              f"-> bo sung anh lop thieu truoc khi train")


def visualize(root: Path, out: Path, n: int, n_classes: int) -> None:
    """Vẽ ngẫu nhiên n ảnh train (box cho detection, polygon cho segmentation)."""
    import cv2
    import numpy as np

    img_dir, lbl_dir = root / "train" / "images", root / "train" / "labels"
    if not img_dir.exists():
        print("Khong co train/images de ve")
        return
    out.mkdir(parents=True, exist_ok=True)
    random.seed(7)
    imgs = [p for p in img_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS]
    for p in random.sample(imgs, min(n, len(imgs))):
        img = cv2.imread(str(p))
        if img is None:
            print(f"Khong doc duoc: {p.name}")
            continue
        h, w = img.shape[:2]
        colors = [(0, 255, 0), (0, 0, 255), (0, 165, 255)]
        lf = lbl_dir / f"{p.stem}.txt"
        if lf.exists():
            for line in lf.read_text(encoding="utf-8").splitlines():
                parts = line.split()
                if classify_row(parts, n_classes) not in ("detection", "segmentation"):
                    continue
                cls = int(float(parts[0]))
                color = colors[cls % len(colors)]
                vals = [float(x) for x in parts[1:]]
                if len(parts) == 5:  # detection: xc yc w h -> 2 goc
                    xc, yc, bw, bh = vals
                    x1, y1 = int((xc - bw / 2) * w), int((yc - bh / 2) * h)
                    x2, y2 = int((xc + bw / 2) * w), int((yc + bh / 2) * h)
                    cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
                    tx, ty = x1, max(15, y1 - 5)
                else:
                    pts = (np.array(vals, dtype=float).reshape(-1, 2)
                           * np.array([w, h])).astype(int)
                    cv2.polylines(img, [pts], True, color, 2)
                    tx, ty = int(pts[:, 0].min()), max(15, int(pts[:, 1].min()) - 5)
                name = CLASS_NAMES[cls] if cls < len(CLASS_NAMES) else str(cls)
                cv2.putText(img, name, (tx, ty),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        cv2.imwrite(str(out / p.name), img)
    print(f"Da ve {min(n, len(imgs))} anh vao {out}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--classes", type=int, default=3)
    ap.add_argument("--visualize", type=int, default=0)
    ap.add_argument("--out", default="qa_preview")
    args = ap.parse_args()

    root = Path(args.root)
    print(f"Dataset: {root}")
    dist_all, stems = Counter(), {}
    for split in ("train", "valid", "test"):
        d, s = check_split(root, split, args.classes)
        dist_all.update(d)
        stems[split] = s
    leak = stems.get("train", set()) & stems.get("valid", set())
    print(f"ro ri train/valid: {len(leak)}" + (f" Vd: {sorted(leak)[:5]}" if leak else " (sach)"))
    warn_imbalance(dist_all)
    if args.visualize:
        visualize(root, Path(args.out), args.visualize, args.classes)
    print("Xong kiem tra")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
