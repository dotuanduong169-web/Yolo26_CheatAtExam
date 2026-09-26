"""Quản lý phiên giám sát: liệt kê, chi tiết, tóm tắt, xóa.
Luồng chính: đọc phiên → gom sự kiện gian lận → tính tỉ lệ sạch → trả về."""

from typing import Optional
from sqlalchemy.orm import Session as DBSession

from core.exceptions import AuthorizationError, NotFoundError, ValidationError
from core.logger import get_logger
from crud.event_crud import list_events_by_session
from crud.session_crud import (
    delete_session_cascade,
    get_session_by_id,
    get_session_count_by_user,
    get_sessions_with_event_count,
)
from models.detected_event import DetectedEvent
from models.monitoring_session import MonitoringSession
from schemas.event import EventResponse
from service.camera_state import CameraState
from utils.label_utils import get_final_label

logger = get_logger(__name__)


def get_session_list(
    db: DBSession,
    user_id: Optional[int],
    skip: int = 0,
    limit: int = 20,
    search: str | None = None,
) -> list[dict]:
    """Liệt kê phiên kèm số sự kiện gian lận. Mới nhất trước."""
    rows = get_sessions_with_event_count(db, user_id, skip, limit, search)
    return [
        {
            "PK_MaPhienGiamSat": s.PK_MaPhienGiamSat,
            "PhongThi": s.PhongThi,
            "MonThi": s.MonThi,
            "ThoiGianBatDau": s.ThoiGianBatDau,
            "ThoiGianKetThuc": s.ThoiGianKetThuc,
            "TrangThai": s.TrangThai,
            "so_su_kien": n,
        }
        for s, n in rows
    ]


def get_session_summary(db: DBSession, user_id: Optional[int]) -> dict:
    """Tóm tắt toàn hệ thống: tổng phiên, phiên đang chạy, tổng sự kiện, sự kiện chờ kiểm tra."""
    total = get_session_count_by_user(db, user_id)

    q_running = db.query(MonitoringSession).filter(
        MonitoringSession.TrangThai == "dang_giam_sat"
    )
    q_events = db.query(DetectedEvent)
    q_pending = db.query(DetectedEvent).filter(
        DetectedEvent.TrangThaiKiemTra == "cho_kiem_tra"
    )
    if user_id is not None:
        q_running = q_running.filter(MonitoringSession.FK_MaNguoiDung == user_id)
        join_cond = (
            DetectedEvent.FK_MaPhienGiamSat == MonitoringSession.PK_MaPhienGiamSat
        )
        q_events = q_events.join(MonitoringSession, join_cond).filter(
            MonitoringSession.FK_MaNguoiDung == user_id
        )
        q_pending = q_pending.join(MonitoringSession, join_cond).filter(
            MonitoringSession.FK_MaNguoiDung == user_id
        )

    return {
        "tong_phien": total,
        "dang_giam_sat": q_running.count(),
        "tong_su_kien": q_events.count(),
        "cho_kiem_tra": q_pending.count(),
    }


def get_session_detail(db: DBSession, session_id: int) -> dict:
    """Chi tiết phiên gồm thống kê sự kiện và danh sách sự kiện.
    Điểm logic: nhãn cuối (người sửa ưu tiên) quyết định phân loại đúng/sai."""
    session = get_session_by_id(db, session_id)
    if not session:
        raise NotFoundError(detail="Session not found")

    events = list_events_by_session(db, session_id, limit=200)
    total = len(events)
    confirmed = sum(1 for e in events if (get_final_label(e) or "") in ("Cheat_Paper", "cellphone"))
    pending = sum(1 for e in events if e.TrangThaiKiemTra == "cho_kiem_tra")

    return {
        "session": {
            "PK_MaPhienGiamSat": session.PK_MaPhienGiamSat,
            "ThoiGianBatDau": session.ThoiGianBatDau,
            "ThoiGianKetThuc": session.ThoiGianKetThuc,
            "TrangThai": session.TrangThai,
            "PhongThi": session.PhongThi,
            "MonThi": session.MonThi,
            "FK_MaNguoiDung": session.FK_MaNguoiDung,
            "FK_MaThietBi": session.FK_MaThietBi,
            "ThoiGianTao": session.ThoiGianTao,
        },
        "tong_su_kien": total,
        "da_xac_minh": total - pending,
        "cho_kiem_tra": pending,
        "ty_le_sach": round(1 - confirmed / total, 3) if total else 1.0,
        "events": [EventResponse.model_validate(e).model_dump() for e in events],
    }


def delete_session(
    db: DBSession,
    session_id: int,
    user_id_check: Optional[int] = None,
) -> dict:
    """Xóa phiên và toàn bộ dữ liệu liên quan.
    Điểm logic: chặn xóa phiên đang chạy; user thường chỉ xóa phiên của mình."""
    state = CameraState()
    if state.is_running() and state.current_session_id == session_id:
        raise ValidationError(detail="Cannot delete a running session")

    session = get_session_by_id(db, session_id)
    if not session:
        raise NotFoundError(detail="Session not found")

    if user_id_check is not None and session.FK_MaNguoiDung != user_id_check:
        raise AuthorizationError(detail="Not allowed to delete this session")

    delete_session_cascade(db, session_id)
    logger.info(f"Session deleted: {session_id}")
    return {"message": "Session deleted successfully"}
