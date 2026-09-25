"""Endpoint lịch sử cho danh sách ca thi, chi tiết và xóa session.
Logic chính: admin xem toàn hệ thống còn user thường chỉ thấy session của mình, chặn xóa session đang chạy.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.dependencies import get_current_user
from core.logger import get_logger
from database.database import get_db
from models.user import User
from schemas.common import MessageResponse
from schemas.session import SessionDetailResponse, SessionListItem, SessionSummaryResponse
from service.session_service import (
    delete_session,
    get_session_detail,
    get_session_list,
    get_session_summary,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/history", tags=["History"])


@router.get("/sessions", response_model=list[SessionListItem])
def get_sessions(
    skip: int = Query(0, ge=0, description="Number of sessions to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max sessions to return"),
    search: str = Query("", description="Search by class name"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Liệt kê ca thi. Có phân trang và tìm theo mã phòng, admin xem hết còn user lọc theo mình."""
    try:
        user_id_filter = None if user.role == "admin" else user.user_id
        return get_session_list(db, user_id_filter, skip, limit, search or None)
    except Exception as exc:
        logger.error(f"Error fetching sessions: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch sessions")


@router.get("/summary", response_model=SessionSummaryResponse)
def get_summary(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lấy tổng số ca thi và số ca trong tháng. Phạm vi lọc theo quyền admin hay user thường."""
    try:
        user_id_filter = None if user.role == "admin" else user.user_id
        return get_session_summary(db, user_id_filter)
    except Exception as exc:
        logger.error(f"Error fetching summary: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch summary")


@router.get("/session/{session_id}", response_model=SessionDetailResponse)
def get_session_detail_endpoint(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lấy chi tiết một ca thi. Gồm tổng hợp gian lận và danh sách frame, lỗi HTTP giữ nguyên mã."""
    try:
        return get_session_detail(db, session_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error fetching session detail: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/session/{session_id}")
def delete_session_endpoint(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Xóa session và toàn bộ dữ liệu liên quan. Chặn xóa ca đang chạy, lỗi thì rollback."""
    try:
        # Xóa theo quyền: admin xóa mọi session, user thường chỉ xóa session của mình
        user_id_check = None if user.role == "admin" else user.user_id
        return delete_session(db, session_id, user_id_check)
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.error(f"Delete session failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
