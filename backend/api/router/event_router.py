"""Endpoint sự kiện phát hiện cho liệt kê, chi tiết và xác minh thủ công.
Logic chính: user_label do người sửa ưu tiên hơn nhãn AI; xác minh ghi người kiểm tra và thời điểm.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.dependencies import get_current_user
from core.exceptions import NotFoundError
from core.logger import get_logger
from crud.event_crud import get_event_by_id, list_events_by_session, verify_event
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
