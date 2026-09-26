"""Quản lý sự kiện phát hiện và bằng chứng trong DB.
Logic chính: chỉ tạo sự kiện cho hành vi gian lận đã debounce; xóa sự kiện kéo bằng chứng.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession, joinedload

from models.detected_event import DetectedEvent
from models.evidence import Evidence


def create_event(
    db: DBSession,
    session_id: int,
    loai_hanh_vi: str,
    nhan_ai: str,
    toa_do: list,
    do_tin_cay: float,
    thoi_gian_phat_hien: Optional[datetime] = None,
) -> DetectedEvent:
    """Tạo sự kiện gian lận. Flush để có ID trước khi gắn bằng chứng cùng transaction."""
    event = DetectedEvent(
        LoaiHanhVi=loai_hanh_vi,
        NhanAI=nhan_ai,
        ToaDo=toa_do,
        DoTinCay=do_tin_cay,
        ThoiGianPhatHien=thoi_gian_phat_hien or datetime.now(timezone.utc),
        FK_MaPhienGiamSat=session_id,
    )
    db.add(event)
    db.flush()
    return event


def create_evidence(
    db: DBSession,
    event_id: int,
    loai_tep: str,
    duong_dan_tep: str,
) -> Evidence:
    """Gắn bằng chứng ảnh/video cho sự kiện."""
    evidence = Evidence(
        LoaiTep=loai_tep,
        DuongDanTep=duong_dan_tep,
        FK_MaSuKien=event_id,
    )
    db.add(evidence)
    db.flush()
    return evidence


def get_event_by_id(db: DBSession, event_id: int) -> Optional[DetectedEvent]:
    """Lấy sự kiện kèm bằng chứng theo khóa chính."""
    return (
        db.query(DetectedEvent)
        .options(joinedload(DetectedEvent.evidences))
        .filter(DetectedEvent.PK_MaSuKien == event_id)
        .first()
    )


def list_events_by_session(
    db: DBSession,
    session_id: int,
    trang_thai: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> list[DetectedEvent]:
    """Liệt kê sự kiện của phiên, mới nhất trước, lọc theo trạng thái kiểm tra."""
    query = (
        db.query(DetectedEvent)
        .options(joinedload(DetectedEvent.evidences))
        .filter(DetectedEvent.FK_MaPhienGiamSat == session_id)
    )
    if trang_thai is not None:
        query = query.filter(DetectedEvent.TrangThaiKiemTra == trang_thai)
    return (
        query.order_by(DetectedEvent.PK_MaSuKien.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def count_events_by_session(db: DBSession, session_id: int) -> int:
    """Đếm sự kiện của một phiên."""
    return (
        db.query(func.count(DetectedEvent.PK_MaSuKien))
        .filter(DetectedEvent.FK_MaPhienGiamSat == session_id)
        .scalar()
        or 0
    )


def count_pending_by_session(db: DBSession, session_id: int) -> int:
    """Đếm sự kiện chờ kiểm tra của một phiên."""
    return (
        db.query(func.count(DetectedEvent.PK_MaSuKien))
        .filter(
            DetectedEvent.FK_MaPhienGiamSat == session_id,
            DetectedEvent.TrangThaiKiemTra == "cho_kiem_tra",
        )
        .scalar()
        or 0
    )


def verify_event(
    db: DBSession,
    event_id: int,
    trang_thai: str,
    nhan_nguoi_dung: Optional[str],
    nguoi_kiem_tra: int,
) -> Optional[DetectedEvent]:
    """Xác minh sự kiện đúng/sai kèm nhãn sửa và người kiểm tra."""
    event = get_event_by_id(db, event_id)
    if not event:
        return None

    event.TrangThaiKiemTra = trang_thai
    event.NhanNguoiDung = nhan_nguoi_dung
    event.FK_MaNguoiKiemTra = nguoi_kiem_tra
    event.ThoiGianKiemTra = datetime.now(timezone.utc)
    db.commit()
    db.refresh(event)
    return event
