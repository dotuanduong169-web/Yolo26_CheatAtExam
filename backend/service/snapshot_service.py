"""Pipeline snapshot cho thi online: ảnh gốc -> chuẩn hoá -> bảng dẫn xuất -> hiển thị.

Nguyên tắc:
- Ảnh nhị phân lưu trên đĩa (images/raw, images/processed), DB chỉ lưu metadata.
- Ghi ảnh gốc + bản ghi tbl_snapshot trước, sau đó mới chuẩn hoá và ghi
  tbl_snapshot_processed. Dashboard đọc ảnh dẫn xuất, không đọc ảnh gốc.
- Hàm capture_snapshot() chạy trong worker nền, không nằm trên đường HTTP ingest.
"""

from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

from core.config import settings
from core.logger import get_logger
from database.database import SessionLocal
from models.camera_stream import CameraStream
from models.snapshot import Snapshot, SnapshotProcessed

logger = get_logger(__name__)

# Chu kỳ lưu snapshot nền cho mỗi luồng (giây). Sự kiện vi phạm vẫn lưu ngay.
SNAPSHOT_INTERVAL_SECONDS = max(5, int(os.getenv("SNAPSHOT_INTERVAL_SECONDS", "30")))
SNAPSHOT_MAX_WIDTH = max(320, int(os.getenv("SNAPSHOT_MAX_WIDTH", "1280")))
SNAPSHOT_THUMB_WIDTH = max(160, int(os.getenv("SNAPSHOT_THUMB_WIDTH", "480")))
SNAPSHOT_JPEG_QUALITY = min(95, max(50, int(os.getenv("SNAPSHOT_JPEG_QUALITY", "85"))))

# Ảnh thumbnail cho nhật ký tick: nhỏ, nhẹ, đủ nhìn hành vi. Raw/annotated đầy đủ
# chỉ lưu khi có sự kiện nghiệp vụ (tbl_evidences).
TIMELINE_IMAGE_MAX_WIDTH = max(160, int(os.getenv("TIMELINE_IMAGE_MAX_WIDTH", "480")))
TIMELINE_JPEG_QUALITY = min(90, max(45, int(os.getenv("TIMELINE_JPEG_QUALITY", "72"))))

RAW_DIR = settings.IMAGE_DIR / "raw"
PROCESSED_DIR = settings.IMAGE_DIR / "processed"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _day_dir(root: Path) -> Path:
    d = root / _now().strftime("%Y%m%d")
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_name(session_id: int, vai_tro: str) -> str:
    stamp = _now().strftime("%Y%m%d_%H%M%S_%f")
    return f"{session_id}_{vai_tro}_{stamp}_{uuid.uuid4().hex[:8]}"


def _decode_size(raw_jpg: bytes) -> tuple[int | None, int | None]:
    """Đọc nhanh kích thước ảnh JPEG, lỗi thì trả (None, None)."""
    try:
        arr = np.frombuffer(raw_jpg, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None:
            return None, None
        h, w = frame.shape[:2]
        return int(w), int(h)
    except Exception:
        return None, None


def save_raw_snapshot(
    session_id: int,
    vai_tro: str,
    raw_jpg: bytes,
    captured_at: datetime | None = None,
) -> int | None:
    """Lưu file JPEG gốc + bản ghi tbl_snapshot ở trạng thái cho_xu_ly.

    Trả về PK_MaSnapshot, hoặc None nếu không lưu được.
    """
    if not raw_jpg:
        return None

    path: Path | None = None
    db = SessionLocal()
    try:
        stream = (
            db.query(CameraStream)
            .filter(
                CameraStream.FK_MaPhienGiamSat == session_id,
                CameraStream.VaiTro == vai_tro,
            )
            .first()
        )
        width, height = _decode_size(raw_jpg)
        path = _day_dir(RAW_DIR) / f"{_safe_name(session_id, vai_tro)}.jpg"
        path.write_bytes(raw_jpg)

        snapshot = Snapshot(
            FK_MaPhienGiamSat=session_id,
            FK_MaStream=stream.PK_MaStream if stream else None,
            VaiTroCamera=vai_tro,
            ThoiGianChup=captured_at or _now(),
            DuongDanGoc=str(path),
            Hash=hashlib.sha256(raw_jpg).hexdigest(),
            KichThuocGoc=len(raw_jpg),
            Width=width,
            Height=height,
            TrangThaiXuLy="cho_xu_ly",
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        return snapshot.PK_MaSnapshot
    except Exception as exc:
        db.rollback()
        # Tránh file mồ côi nếu không ghi được metadata.
        if path is not None:
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass
        logger.warning(f"save_raw_snapshot failed (session={session_id}, role={vai_tro}): {exc}")
        return None
    finally:
        db.close()


def _save_image(img: Image.Image, path: Path) -> tuple[int, int, int]:
    """Lưu JPEG, trả (width, height, bytes)."""
    img.save(path, format="JPEG", quality=SNAPSHOT_JPEG_QUALITY, optimize=True)
    return img.width, img.height, path.stat().st_size


def _resize_max_width(img: Image.Image, max_width: int) -> Image.Image:
    if img.width <= max_width:
        return img.copy()
    ratio = max_width / float(img.width)
    return img.resize((max_width, max(1, int(img.height * ratio))), Image.Resampling.LANCZOS)


def normalize_snapshot(snapshot_id: int, annotated_frame: np.ndarray | None = None) -> bool:
    """Chuẩn hoá ảnh gốc và ghi các biến thể vào tbl_snapshot_processed.

    - normalized: ảnh hiển thị chính (EXIF rotate, resize, strip EXIF).
    - thumbnail: ảnh nhỏ cho lưới giám thị.
    - annotated: khung hình đã vẽ overlay AI (nếu có).
    """
    db = SessionLocal()
    snapshot = None
    try:
        snapshot = db.query(Snapshot).filter(Snapshot.PK_MaSnapshot == snapshot_id).first()
        if snapshot is None:
            return False
        snapshot.TrangThaiXuLy = "dang_xu_ly"
        db.commit()

        raw_path = Path(snapshot.DuongDanGoc)
        if not raw_path.is_file():
            raise FileNotFoundError(f"raw snapshot missing: {raw_path}")

        # Ghi nhớ biến thể cũ để dọn file mồ côi nếu chạy lại (idempotent).
        old_paths = {
            row.DuongDanTep
            for row in db.query(SnapshotProcessed)
            .filter(SnapshotProcessed.FK_MaSnapshot == snapshot_id)
            .all()
        }

        with Image.open(raw_path) as im:
            img = ImageOps.exif_transpose(im).convert("RGB")
            out_dir = _day_dir(PROCESSED_DIR)
            stem = f"{snapshot_id}_{snapshot.VaiTroCamera}"

            norm_img = _resize_max_width(img, SNAPSHOT_MAX_WIDTH)
            norm_path = out_dir / f"{stem}_normalized.jpg"
            nw, nh, nsize = _save_image(norm_img, norm_path)

            thumb_img = _resize_max_width(img, SNAPSHOT_THUMB_WIDTH)
            thumb_path = out_dir / f"{stem}_thumb.jpg"
            tw, th, tsize = _save_image(thumb_img, thumb_path)

            processed = [
                SnapshotProcessed(
                    FK_MaSnapshot=snapshot_id,
                    LoaiAnh="normalized",
                    DuongDanTep=str(norm_path),
                    Width=nw,
                    Height=nh,
                    KichThuoc=nsize,
                ),
                SnapshotProcessed(
                    FK_MaSnapshot=snapshot_id,
                    LoaiAnh="thumbnail",
                    DuongDanTep=str(thumb_path),
                    Width=tw,
                    Height=th,
                    KichThuoc=tsize,
                ),
            ]

            if annotated_frame is not None and getattr(annotated_frame, "size", 0):
                ann_path = out_dir / f"{stem}_annotated.jpg"
                ok, buf = cv2.imencode(
                    ".jpg",
                    annotated_frame,
                    [cv2.IMWRITE_JPEG_QUALITY, SNAPSHOT_JPEG_QUALITY],
                )
                if ok:
                    ann_path.write_bytes(buf.tobytes())
                    ah, aw = annotated_frame.shape[:2]
                    processed.append(
                        SnapshotProcessed(
                            FK_MaSnapshot=snapshot_id,
                            LoaiAnh="annotated",
                            DuongDanTep=str(ann_path),
                            Width=int(aw),
                            Height=int(ah),
                            KichThuoc=ann_path.stat().st_size,
                        )
                    )

            # Xoá biến thể cũ (nếu chạy lại) để không nhân đôi bản ghi.
            db.query(SnapshotProcessed).filter(
                SnapshotProcessed.FK_MaSnapshot == snapshot_id
            ).delete(synchronize_session=False)

            db.add_all(processed)
            snapshot.TrangThaiXuLy = "xong"
            snapshot.GhiChu = None
            db.commit()

        # Xoá file dẫn xuất cũ không còn bản ghi tương ứng (vd. annotated bị bỏ).
        for stale in old_paths - {p.DuongDanTep for p in processed}:
            try:
                Path(stale).unlink(missing_ok=True)
            except OSError:
                pass
        return True
    except Exception as exc:
        db.rollback()
        try:
            snapshot = db.query(Snapshot).filter(Snapshot.PK_MaSnapshot == snapshot_id).first()
            if snapshot is not None:
                snapshot.TrangThaiXuLy = "loi"
                snapshot.GhiChu = str(exc)[:1000]
                db.commit()
        except Exception:
            db.rollback()
        logger.warning(f"normalize_snapshot failed (snapshot={snapshot_id}): {exc}")
        return False
    finally:
        db.close()


def capture_snapshot(
    session_id: int,
    vai_tro: str,
    raw_jpg: bytes,
    annotated_frame: np.ndarray | None = None,
    captured_at: datetime | None = None,
) -> int | None:
    """Pipeline đầy đủ: lưu raw trước, sau đó chuẩn hoá và ghi bảng dẫn xuất."""
    snapshot_id = save_raw_snapshot(session_id, vai_tro, raw_jpg, captured_at=captured_at)
    if snapshot_id is None:
        return None
    normalize_snapshot(snapshot_id, annotated_frame=annotated_frame)
    return snapshot_id


def capture_timeline_snapshot(
    session_id: int,
    vai_tro: str,
    frame: np.ndarray,
    captured_at: datetime | None = None,
) -> int | None:
    """Lưu một thumbnail nhẹ cho nhật ký tick (không lưu raw/normalized).

    Dùng đúng ảnh annotated đã qua AI để timeline thấy khung nhận diện. Chỉ một
    file JPEG mỗi tick, giảm mạnh dung lượng so với pipeline snapshot đầy đủ.
    """
    if frame is None or getattr(frame, "size", 0) == 0:
        return None

    path: Path | None = None
    db = SessionLocal()
    try:
        img = frame
        if img.shape[1] > TIMELINE_IMAGE_MAX_WIDTH:
            ratio = TIMELINE_IMAGE_MAX_WIDTH / float(img.shape[1])
            img = cv2.resize(
                img,
                (TIMELINE_IMAGE_MAX_WIDTH, max(1, int(img.shape[0] * ratio))),
                interpolation=cv2.INTER_AREA,
            )

        ok, buf = cv2.imencode(
            ".jpg",
            img,
            [cv2.IMWRITE_JPEG_QUALITY, TIMELINE_JPEG_QUALITY],
        )
        if not ok:
            return None

        jpg_bytes = buf.tobytes()
        stamp_dt = captured_at or _now()
        out_dir = PROCESSED_DIR / stamp_dt.strftime("%Y%m%d")
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{_safe_name(session_id, vai_tro)}_timeline.jpg"
        path.write_bytes(jpg_bytes)

        h, w = img.shape[:2]
        snapshot = Snapshot(
            FK_MaPhienGiamSat=session_id,
            VaiTroCamera=vai_tro,
            ThoiGianChup=stamp_dt,
            DuongDanGoc=str(path),
            Hash=hashlib.sha256(jpg_bytes).hexdigest(),
            KichThuocGoc=len(jpg_bytes),
            Width=int(w),
            Height=int(h),
            TrangThaiXuLy="xong",
        )
        db.add(snapshot)
        db.flush()
        db.add(
            SnapshotProcessed(
                FK_MaSnapshot=snapshot.PK_MaSnapshot,
                LoaiAnh="thumbnail",
                DuongDanTep=str(path),
                Width=int(w),
                Height=int(h),
                KichThuoc=len(jpg_bytes),
            )
        )
        db.commit()
        return snapshot.PK_MaSnapshot
    except Exception as exc:
        db.rollback()
        if path is not None:
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass
        logger.warning(
            f"capture_timeline_snapshot failed (session={session_id}, role={vai_tro}): {exc}"
        )
        return None
    finally:
        db.close()


def latest_snapshot_path(
    db,
    session_id: int,
    vai_tro: str | None = None,
    loai_anh: str = "thumbnail",
) -> str | None:
    """Đường dẫn ảnh dẫn xuất mới nhất của phiên/luồng (nếu file còn tồn tại)."""
    query = (
        db.query(SnapshotProcessed.DuongDanTep)
        .join(Snapshot, Snapshot.PK_MaSnapshot == SnapshotProcessed.FK_MaSnapshot)
        .filter(
            Snapshot.FK_MaPhienGiamSat == session_id,
            Snapshot.TrangThaiXuLy == "xong",
            SnapshotProcessed.LoaiAnh == loai_anh,
        )
    )
    if vai_tro:
        query = query.filter(Snapshot.VaiTroCamera == vai_tro)
    rows = (
        query.order_by(Snapshot.ThoiGianChup.desc(), Snapshot.PK_MaSnapshot.desc())
        .limit(10)
        .all()
    )
    for (path_str,) in rows:
        path = Path(path_str)
        if path.is_file():
            return str(path)
    return None
