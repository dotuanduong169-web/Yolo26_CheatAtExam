"""Endpoint thống kê cho tổng hợp ngày, tuần và toàn hệ thống.
Logic chính: sleeping là số vật gian lận (Cheat_Paper và cellphone), admin xem hết còn user lọc theo mình.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.dependencies import get_current_user
from core.logger import get_logger
from database.database import get_db
from models.user import User
from schemas.statistics import DailyStatItem, DateStatItem, StatsSummaryResponse, WeeklyStatItem
from service.statistics_service import (
    get_daily_stats,
    get_stats_by_date,
    get_stats_summary,
    get_weekly_stats,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/stats", tags=["Statistics"])


@router.get("/daily", response_model=list[DailyStatItem])
def stats_daily(
    days: int = Query(30, ge=1, le=365, description="Number of past days"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lấy thống kê gom theo ngày. Phạm vi N ngày gần nhất, lọc theo quyền admin hay user."""
    try:
        user_id_filter = None if user.role == "admin" else user.user_id
        return get_daily_stats(db, user_id_filter, days)
    except Exception as exc:
        logger.error(f"Error fetching daily stats: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch daily statistics")


@router.get("/by-date", response_model=list[DateStatItem])
def stats_by_date(
    days: int = Query(30, ge=1, le=365, description="Number of past days"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lấy số vật gian lận theo từng ngày. Dùng vẽ biểu đồ cảnh báo N ngày gần nhất."""
    try:
        user_id_filter = None if user.role == "admin" else user.user_id
        return get_stats_by_date(db, user_id_filter, days)
    except Exception as exc:
        logger.error(f"Error fetching by-date stats: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch date statistics")


@router.get("/weekly", response_model=list[WeeklyStatItem])
def stats_weekly(
    weeks: int = Query(4, ge=1, le=52, description="Number of past weeks"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lấy thống kê gom theo tuần. Dùng cho biểu đồ xu hướng N tuần gần nhất."""
    try:
        user_id_filter = None if user.role == "admin" else user.user_id
        return get_weekly_stats(db, user_id_filter, weeks)
    except Exception as exc:
        logger.error(f"Error fetching weekly stats: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch weekly statistics")


@router.get("/summary", response_model=StatsSummaryResponse)
def stats_summary(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lấy tổng hợp toàn hệ thống. Gồm tổng lượt phát hiện và tỉ lệ bài sạch trung bình."""
    try:
        user_id_filter = None if user.role == "admin" else user.user_id
        return get_stats_summary(db, user_id_filter)
    except Exception as exc:
        logger.error(f"Error fetching summary: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch summary")
