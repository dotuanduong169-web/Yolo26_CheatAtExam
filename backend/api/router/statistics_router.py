"""Endpoint thống kê cho tổng hợp ngày, tuần và toàn hệ thống.
Logic chính: sleeping là số vật gian lận (Cheat_Paper và cellphone), admin xem hết còn user lọc theo mình.
Lưu ý: tên key sleeping là lịch sử, giữ nguyên để tương thích DB và API.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from core.dependencies import get_current_user
from core.logger import get_logger
from database.database import get_db
from models.user import User
from schemas.statistics import (
    CandidateStatItem,
    DailyStatItem,
    DateStatItem,
    StatsOverviewResponse,
    StatsSummaryResponse,
    TimelinePage,
    WeeklyStatItem,
)
from service.statistics_service import (
    get_daily_stats,
    get_stats_by_date,
    get_stats_summary,
    get_weekly_stats,
)
from service.timeline_service import (
    get_candidate_stats,
    get_overview,
    get_timeline_image_path,
    list_timeline,
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
        user_id_filter = None if user.VaiTro == "admin" else user.PK_MaNguoiDung
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
        user_id_filter = None if user.VaiTro == "admin" else user.PK_MaNguoiDung
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
        user_id_filter = None if user.VaiTro == "admin" else user.PK_MaNguoiDung
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
        user_id_filter = None if user.VaiTro == "admin" else user.PK_MaNguoiDung
        return get_stats_summary(db, user_id_filter)
    except Exception as exc:
        logger.error(f"Error fetching summary: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch summary")


@router.get("/overview", response_model=StatsOverviewResponse)
def stats_overview(
    session_id: Optional[int] = Query(None, description="Mã ca thi cha; bỏ trống để xem tất cả"),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """KPI thống kê gắn thí sinh: tổng thí sinh, thí sinh có cảnh báo, cảnh báo, độ trễ."""
    try:
        user_id_filter = None if user.VaiTro == "admin" else user.PK_MaNguoiDung
        return get_overview(db, session_id, user_id_filter, from_date, to_date)
    except Exception as exc:
        logger.error(f"Error fetching stats overview: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch stats overview")


@router.get("/candidates", response_model=list[CandidateStatItem])
def stats_candidates(
    session_id: Optional[int] = Query(None, description="Mã ca thi cha"),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Tổng hợp số cảnh báo theo từng thí sinh trong ca (hoặc toàn hệ thống)."""
    try:
        user_id_filter = None if user.VaiTro == "admin" else user.PK_MaNguoiDung
        return get_candidate_stats(db, session_id, user_id_filter, from_date, to_date)
    except Exception as exc:
        logger.error(f"Error fetching candidate stats: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch candidate stats")


@router.get("/timeline", response_model=TimelinePage)
def stats_timeline(
    session_id: Optional[int] = Query(None, description="Mã ca thi cha"),
    candidate_id: Optional[int] = Query(None),
    only_alerts: bool = Query(True, description="True: chỉ tick có cảnh báo"),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
    include_image: bool = Query(True),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Timeline cảnh báo của TẤT CẢ thí sinh, kèm ảnh thumbnail + thời gian + SBD."""
    try:
        user_id_filter = None if user.VaiTro == "admin" else user.PK_MaNguoiDung
        return list_timeline(
            db,
            session_id=session_id,
            candidate_id=candidate_id,
            only_alerts=only_alerts,
            from_dt=from_date,
            to_dt=to_date,
            skip=skip,
            limit=limit,
            user_id=user_id_filter,
            include_image=include_image,
        )
    except Exception as exc:
        logger.error(f"Error fetching timeline: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch timeline")


@router.get("/timeline/{entry_id}/file")
def stats_timeline_file(
    entry_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Tải thumbnail minh chứng của một tick timeline."""
    user_id_filter = None if user.VaiTro == "admin" else user.PK_MaNguoiDung
    path = get_timeline_image_path(db, entry_id, user_id_filter)
    if not path:
        raise HTTPException(status_code=404, detail="Timeline image not found")
    return FileResponse(path)


@router.get("/distribution")
def stats_distribution(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lấy phân bố hành vi gian lận thực tế từ cơ sở dữ liệu."""
    try:
        from service.statistics_service import get_behavior_distribution
        user_id_filter = None if user.VaiTro == "admin" else user.PK_MaNguoiDung
        return get_behavior_distribution(db, user_id_filter)
    except Exception as exc:
        logger.error(f"Error fetching distribution: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch distribution")

