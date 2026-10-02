"""Endpoint sự kiện phát hiện cho liệt kê, chi tiết và xác minh thủ công.
Logic chính: user_label do người sửa ưu tiên hơn nhãn AI; xác minh ghi người kiểm tra và thời điểm.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from core.dependencies import get_current_user
from core.exceptions import NotFoundError
from core.logger import get_logger
from crud.event_crud import get_event_by_id, get_evidence_by_id, list_events_by_session, verify_event
from database.database import get_db
from models.user import User
from schemas.event import EventResponse, EventVerify

logger = get_logger(__name__)
router = APIRouter(prefix="/events", tags=["Events"])


@router.get("/session/{session_id}", response_model=list[EventResponse])
def get_session_events(
    session_id: int,
    trang_thai: str | None = Query(None, pattern="^(cho_kiem_tra|dung|sai)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Liệt kê sự kiện gian lận của phiên, mới nhất trước, lọc theo trạng thái kiểm tra."""
    try:
        return list_events_by_session(db, session_id, trang_thai, skip, limit)
    except Exception as exc:
        logger.error(f"Error fetching events: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch events")


@router.get("/{event_id}", response_model=EventResponse)
def get_event(
    event_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lấy chi tiết một sự kiện kèm bằng chứng và tọa độ để vẽ lại."""
    event = get_event_by_id(db, event_id)
    if not event:
        raise NotFoundError(detail="Event not found")
    return event


@router.patch("/{event_id}", response_model=EventResponse)
def verify_event_endpoint(
    event_id: int,
    payload: EventVerify,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Xác minh sự kiện đúng/sai kèm nhãn sửa. Ghi người kiểm tra và thời điểm."""
    event = verify_event(
        db,
        event_id,
        payload.TrangThaiKiemTra,
        payload.NhanNguoiDung,
        user.PK_MaNguoiDung,
    )
    if not event:
        raise NotFoundError(detail="Event not found")
    return event


@router.get("/evidences/{evidence_id}/file")
def get_evidence_file(
    evidence_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Tải file ảnh/video bằng chứng. Yêu cầu đăng nhập."""
    from pathlib import Path

    evidence = get_evidence_by_id(db, evidence_id)
    if not evidence:
        raise NotFoundError(detail="Evidence not found")
    path = Path(evidence.DuongDanTep)
    if not path.is_file():
        raise NotFoundError(detail="Evidence file missing")
    return FileResponse(path)


@router.get("/system/notifications")
def get_system_notifications_endpoint(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Tổng hợp thông báo hệ thống và cảnh báo vi phạm mới nhất."""
    from datetime import datetime
    from crud.event_crud import count_total_pending_events, list_recent_pending_events
    from crud.session_crud import get_active_session

    total_pending = count_total_pending_events(db)
    recent_events = list_recent_pending_events(db, limit=6)
    active_session = get_active_session(db)

    behavior_names = {
        "Cheat_Paper": "Sử dụng tài liệu (Phao thi)",
        "cellphone": "Sử dụng điện thoại di động",
        "Head_Turn": "Quay đầu / Nhìn bài",
        "quay_dau": "Quay đầu bất thường (>45°)",
        "quay_sau": "Quay người về sau trao đổi bài",
        "cui_xuong": "Cúi đầu nhìn tài liệu gầm bàn",
        "Answer_paper": "Giấy thi hợp lệ",
    }

    alerts = []
    for ev in recent_events:
        raw_b = ev.LoaiHanhVi or ""
        friendly_b = behavior_names.get(raw_b, raw_b)
        alerts.append({
            "id": ev.PK_MaSuKien,
            "session_id": ev.FK_MaPhienGiamSat,
            "behavior": raw_b,
            "behavior_label": friendly_b,
            "confidence": round(float(ev.DoTinCay or 0) * 100, 1),
            "detected_at": str(ev.ThoiGianPhatHien)[:19] if ev.ThoiGianPhatHien else "",
            "status": ev.TrangThaiKiemTra,
        })

    session_info = None
    if active_session:
        session_info = {
            "session_id": active_session.PK_MaPhienGiamSat,
            "room": active_session.PhongThi or "Chưa đặt phòng",
            "subject": active_session.MonThi or "Chưa đặt môn",
            "started_at": str(active_session.ThoiGianBatDau)[:19] if active_session.ThoiGianBatDau else "",
        }

    return {
        "total_pending": total_pending,
        "alerts": alerts,
        "active_session": session_info,
        "system_status": "online",
        "server_time": datetime.now().strftime("%H:%M:%S %d/%m/%Y"),
    }

