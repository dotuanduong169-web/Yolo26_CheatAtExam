"""Quản lý sự kiện phát hiện và bằng chứng trong DB.
Logic chính: chỉ tạo sự kiện cho hành vi gian lận đã debounce; xóa sự kiện kéo bằng chứng.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession, joinedload

from models.detected_event import DetectedEvent
from models.evidence import Evidence
from models.monitoring_session import MonitoringSession


def _with_event_relations(query):
    """Nạp sẵn bằng chứng + phiên + thí sinh để trả EventResponse đầy đủ."""
    return query.options(
        joinedload(DetectedEvent.evidences),
        joinedload(DetectedEvent.session).joinedload(MonitoringSession.candidate),
    )


def create_event(
    db: DBSession,
    session_id: int,
    loai_hanh_vi: str,
    toa_do: list,
    do_tin_cay: float,
    thoi_gian_phat_hien: Optional[datetime] = None,
    nhan_ai: Optional[str] = None,
    vai_tro_camera: Optional[str] = "front",
) -> DetectedEvent:
    """Tạo sự kiện gian lận. Flush để có ID trước khi gắn bằng chứng cùng transaction."""
    event = DetectedEvent(
        LoaiHanhVi=loai_hanh_vi,
        ToaDo=toa_do,
        DoTinCay=do_tin_cay,
        ThoiGianPhatHien=thoi_gian_phat_hien or datetime.now(timezone.utc),
        FK_MaPhienGiamSat=session_id,
        VaiTroCamera=vai_tro_camera or "front",
    )
    db.add(event)
    db.flush()
    return event


def create_evidence(
    db: DBSession,
    event_id: int,
    loai_tep: str,
    duong_dan_tep: str,
    vai_tro_camera: Optional[str] = "front",
) -> Evidence:
    """Gắn bằng chứng ảnh/video cho sự kiện."""
    evidence = Evidence(
        LoaiTep=loai_tep,
        DuongDanTep=duong_dan_tep,
        FK_MaSuKien=event_id,
        VaiTroCamera=vai_tro_camera or "front",
    )
    db.add(evidence)
    db.flush()
    return evidence


def get_event_by_id(db: DBSession, event_id: int) -> Optional[DetectedEvent]:
    """Lấy sự kiện kèm bằng chứng theo khóa chính."""
    return (
        _with_event_relations(db.query(DetectedEvent))
        .filter(DetectedEvent.PK_MaSuKien == event_id)
        .first()
    )


def get_evidence_by_id(db: DBSession, evidence_id: int) -> Optional[Evidence]:
    """Lấy một bằng chứng theo khóa chính."""
    return (
        db.query(Evidence)
        .filter(Evidence.PK_MaBangChung == evidence_id)
        .first()
    )


def list_events_by_sessions(
    db: DBSession,
    session_ids: list[int],
    trang_thai: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> list[DetectedEvent]:
    """Liệt kê sự kiện của nhiều phiên (ca thi cha + phiên con), mới nhất trước.

    Điểm logic: ca thi online lưu sự kiện ở phiên con của từng thí sinh, nên khi
    xem theo ca thi cha phải gom nhiều phiên trong cùng một truy vấn.
    """
    if not session_ids:
        return []
    query = (
        _with_event_relations(db.query(DetectedEvent))
        .filter(DetectedEvent.FK_MaPhienGiamSat.in_(session_ids))
    )
    if trang_thai is not None:
        query = query.filter(DetectedEvent.TrangThaiKiemTra == trang_thai)
    return (
        query.order_by(DetectedEvent.PK_MaSuKien.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def list_events_by_session(
    db: DBSession,
    session_id: int,
    trang_thai: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> list[DetectedEvent]:
    """Liệt kê sự kiện của một phiên, mới nhất trước, lọc theo trạng thái kiểm tra."""
    return list_events_by_sessions(db, [session_id], trang_thai, skip, limit)


def list_all_events_crud(
    db: DBSession,
    trang_thai: Optional[str] = None,
    skip: int = 0,
    limit: int = 200,
) -> list[DetectedEvent]:
    """Liệt kê toàn bộ sự kiện của tất cả các phiên, mới nhất trước."""
    query = _with_event_relations(db.query(DetectedEvent))
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
    if nhan_nguoi_dung:
        event.LoaiHanhVi = nhan_nguoi_dung
    event.FK_MaNguoiKiemTra = nguoi_kiem_tra
    db.commit()
    db.refresh(event)
    return event


def count_total_pending_events(db: DBSession) -> int:
    """Đếm tổng số sự kiện chờ kiểm tra trên toàn hệ thống."""
    return (
        db.query(func.count(DetectedEvent.PK_MaSuKien))
        .filter(DetectedEvent.TrangThaiKiemTra == "cho_kiem_tra")
        .scalar()
        or 0
    )


def list_recent_pending_events(db: DBSession, limit: int = 5) -> list[DetectedEvent]:
    """Lấy danh sách các sự kiện vi phạm chờ kiểm tra mới nhất."""
    return (
        _with_event_relations(db.query(DetectedEvent))
        .filter(DetectedEvent.TrangThaiKiemTra == "cho_kiem_tra")
        .order_by(DetectedEvent.PK_MaSuKien.desc())
        .limit(limit)
        .all()
    )

