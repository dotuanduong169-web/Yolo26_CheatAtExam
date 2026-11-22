"""Quản lý phiên giám sát gắn thiết bị biên và phòng thi.
Logic chính: mở phiên gắn user + thiết bị; xóa phiên kéo theo sự kiện và bằng chứng.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from core.logger import get_logger
from models.candidate import Candidate
from models.detected_event import DetectedEvent
from models.monitoring_session import MonitoringSession

logger = get_logger(__name__)


def get_session_scope_ids(db: DBSession, session_id: int) -> list[int]:
    """Trả về [session_id] + các phiên con nếu đây là ca thi cha.

    Điểm logic: sự kiện của ca thi online được ghi vào phiên con của từng thí sinh,
    nên khi xem/tổng hợp theo ca thi cha phải gom cả sự kiện của các phiên con.
    """
    scope = [session_id]
    child_rows = (
        db.query(MonitoringSession.PK_MaPhienGiamSat)
        .join(Candidate, Candidate.PK_MaThiSinh == MonitoringSession.FK_MaThiSinh)
        .filter(Candidate.FK_MaPhienGiamSat == session_id)
        .all()
    )
    scope.extend(row[0] for row in child_rows)
    return scope


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
    query = db.query(MonitoringSession).filter(MonitoringSession.FK_MaThiSinh.is_(None))
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
    """Liệt kê ca thi kèm tổng số sự kiện, gồm cả phiên con của thí sinh.

    Điểm logic: sự kiện AI ghi vào phiên con (FK_MaThiSinh khác NULL), nên nếu chỉ
    đếm trực tiếp trên phiên cha thì ca thi online luôn hiện 0 sự kiện.
    """
    query = db.query(MonitoringSession).filter(MonitoringSession.FK_MaThiSinh.is_(None))
    if user_id is not None:
        query = query.filter(MonitoringSession.FK_MaNguoiDung == user_id)
    if search:
        like = f"%{search}%"
        query = query.filter(
            (MonitoringSession.PhongThi.ilike(like)) | (MonitoringSession.MonThi.ilike(like))
        )
    sessions = (
        query.order_by(MonitoringSession.PK_MaPhienGiamSat.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    if not sessions:
        return []

    parent_ids = [s.PK_MaPhienGiamSat for s in sessions]
    # Ánh xạ phiên (cha + con) về ca thi cha để cộng dồn sự kiện.
    scope_parent = {parent_id: parent_id for parent_id in parent_ids}
    child_rows = (
        db.query(MonitoringSession.PK_MaPhienGiamSat, Candidate.FK_MaPhienGiamSat)
        .join(Candidate, Candidate.PK_MaThiSinh == MonitoringSession.FK_MaThiSinh)
        .filter(Candidate.FK_MaPhienGiamSat.in_(parent_ids))
        .all()
    )
    for child_id, parent_id in child_rows:
        scope_parent[child_id] = parent_id

    counts = dict(
        db.query(DetectedEvent.FK_MaPhienGiamSat, func.count(DetectedEvent.PK_MaSuKien))
        .filter(DetectedEvent.FK_MaPhienGiamSat.in_(list(scope_parent.keys())))
        .group_by(DetectedEvent.FK_MaPhienGiamSat)
        .all()
    )
    totals = {parent_id: 0 for parent_id in parent_ids}
    for session_id, parent_id in scope_parent.items():
        totals[parent_id] += counts.get(session_id, 0)

    return [(s, totals[s.PK_MaPhienGiamSat]) for s in sessions]


def get_session_count_by_user(db: DBSession, user_id: Optional[int] = None, search: Optional[str] = None) -> int:
    """Đếm tổng số phiên, lọc theo user và từ khóa phòng/môn khi cần."""
    query = db.query(func.count(MonitoringSession.PK_MaPhienGiamSat)).filter(
        MonitoringSession.FK_MaThiSinh.is_(None)
    )
    if user_id is not None:
        query = query.filter(MonitoringSession.FK_MaNguoiDung == user_id)
    if search:
        like = f"%{search}%"
        query = query.filter(
            (MonitoringSession.PhongThi.ilike(like)) | (MonitoringSession.MonThi.ilike(like))
        )
    return query.scalar() or 0


def get_monthly_session_count_by_user(db: DBSession, user_id: Optional[int] = None) -> int:
    """Đếm phiên trong 30 ngày gần nhất, lọc theo user khi cần (chỉ đếm ca thi cha, bỏ qua phiên con thí sinh)."""
    since = datetime.now(timezone.utc).timestamp() - 30 * 24 * 3600
    query = (
        db.query(func.count(MonitoringSession.PK_MaPhienGiamSat))
        .filter(func.extract("epoch", MonitoringSession.ThoiGianBatDau) >= since)
        .filter(MonitoringSession.FK_MaThiSinh.is_(None))
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


def get_active_session(db: DBSession) -> Optional[MonitoringSession]:
    """Lấy ca thi cha đang diễn ra gần nhất (bỏ qua phiên con của thí sinh)."""
    return (
        db.query(MonitoringSession)
        .filter(
            MonitoringSession.TrangThai == "dang_giam_sat",
            MonitoringSession.ThoiGianKetThuc.is_(None),
            MonitoringSession.FK_MaThiSinh.is_(None),
        )
        .order_by(MonitoringSession.PK_MaPhienGiamSat.desc())
        .first()
    )

