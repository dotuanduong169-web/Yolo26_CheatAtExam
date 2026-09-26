"""Quản lý phiên giám sát gắn thiết bị biên và phòng thi.
Logic chính: mở phiên gắn user + thiết bị; xóa phiên kéo theo sự kiện và bằng chứng.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from core.logger import get_logger
from models.detected_event import DetectedEvent
from models.monitoring_session import MonitoringSession

logger = get_logger(__name__)


def create_session(
    db: DBSession,
    user_id: int,
    device_id: int,
    phong_thi: Optional[str] = None,
    mon_thi: Optional[str] = None,
) -> MonitoringSession:
    """Tạo phiên giám sát mới. Ghi giờ bắt đầu UTC rồi commit để lấy ID ngay."""
    session = MonitoringSession(
        ThoiGianBatDau=datetime.now(timezone.utc),
        PhongThi=phong_thi,
        MonThi=mon_thi,
        FK_MaNguoiDung=user_id,
        FK_MaThietBi=device_id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def end_session(db: DBSession, session_id: int) -> None:
    """Kết thúc phiên. Ghi giờ kết thúc UTC và trạng thái, bỏ qua nếu không tồn tại."""
    session = (
        db.query(MonitoringSession)
        .filter(MonitoringSession.PK_MaPhienGiamSat == session_id)
        .first()
    )
    if session and session.TrangThai != "ket_thuc":
        session.ThoiGianKetThuc = datetime.now(timezone.utc)
        session.TrangThai = "ket_thuc"
        db.commit()


def get_session_by_id(
    db: DBSession,
    session_id: int,
) -> Optional[MonitoringSession]:
    """Lấy một phiên theo khóa chính."""
    return (
        db.query(MonitoringSession)
        .filter(MonitoringSession.PK_MaPhienGiamSat == session_id)
        .first()
    )


def get_sessions_by_user(
    db: DBSession,
    user_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
) -> list[MonitoringSession]:
    """Liệt kê phiên mới nhất trước. Lọc theo user và tìm theo phòng/môn thi."""
    query = db.query(MonitoringSession)
    if user_id is not None:
        query = query.filter(MonitoringSession.FK_MaNguoiDung == user_id)
    if search:
        like = f"%{search}%"
        query = query.filter(
            (MonitoringSession.PhongThi.ilike(like)) | (MonitoringSession.MonThi.ilike(like))
        )
    return (
        query.order_by(MonitoringSession.PK_MaPhienGiamSat.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_sessions_with_event_count(
    db: DBSession,
    user_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
) -> list[tuple]:
    """Liệt kê phiên kèm số sự kiện gian lận trong một truy vấn."""
    query = (
        db.query(MonitoringSession, func.count(DetectedEvent.PK_MaSuKien))
        .outerjoin(
            DetectedEvent,
            DetectedEvent.FK_MaPhienGiamSat == MonitoringSession.PK_MaPhienGiamSat,
        )
        .group_by(MonitoringSession.PK_MaPhienGiamSat)
    )
    if user_id is not None:
        query = query.filter(MonitoringSession.FK_MaNguoiDung == user_id)
    if search:
        like = f"%{search}%"
        query = query.filter(
            (MonitoringSession.PhongThi.ilike(like)) | (MonitoringSession.MonThi.ilike(like))
        )
    return (
        query.order_by(MonitoringSession.PK_MaPhienGiamSat.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_session_count_by_user(db: DBSession, user_id: Optional[int] = None) -> int:
    """Đếm tổng số phiên, lọc theo user khi cần."""
    query = db.query(func.count(MonitoringSession.PK_MaPhienGiamSat))
    if user_id is not None:
        query = query.filter(MonitoringSession.FK_MaNguoiDung == user_id)
    return query.scalar() or 0


def get_monthly_session_count_by_user(db: DBSession, user_id: Optional[int] = None) -> int:
    """Đếm phiên trong 30 ngày gần nhất, lọc theo user khi cần."""
    since = datetime.now(timezone.utc).timestamp() - 30 * 24 * 3600
    query = db.query(func.count(MonitoringSession.PK_MaPhienGiamSat)).filter(
        func.extract("epoch", MonitoringSession.ThoiGianBatDau) >= since
    )
    if user_id is not None:
        query = query.filter(MonitoringSession.FK_MaNguoiDung == user_id)
    return query.scalar() or 0


def delete_session_cascade(db: DBSession, session_id: int) -> bool:
    """Xóa phiên và toàn bộ sự kiện, bằng chứng, thống kê liên quan."""
    session = get_session_by_id(db, session_id)
    if not session:
        return False

    db.delete(session)
    db.commit()
    return True
