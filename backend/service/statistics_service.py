"""Tổng hợp thống kê gian lận: theo ngày, theo tuần ISO, theo khoảng ngày, toàn cục.
Luồng chính: lọc theo người dùng qua phiên giám sát → gom nhóm theo mốc thời gian."""

from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from models.monitoring_session import MonitoringSession
from models.statistic import Statistic
from core.logger import get_logger

logger = get_logger(__name__)


def _join_user(query, user_id: Optional[int]):
    """Lọc thống kê theo người sở hữu phiên. None nghĩa là toàn hệ thống."""
    if user_id is None:
        return query
    return query.join(
        MonitoringSession, Statistic.session_id == MonitoringSession.PK_MaPhienGiamSat
    ).filter(MonitoringSession.FK_MaNguoiDung == user_id)


def get_daily_stats(db: DBSession, user_id: Optional[int], days: int = 30) -> list[dict]:
    """Gộp số liệu theo từng ngày trong N ngày gần nhất.
    Điểm logic: tỉ lệ sạch = 1 - gian lận/tổng; tổng bằng 0 thì coi như 0."""
    query = _join_user(
        db.query(
            func.date(Statistic.timestamp),
            func.sum(Statistic.total_students),
            func.sum(Statistic.sleeping_count),
        ),
        user_id,
    )

    results = (
        query.group_by(func.date(Statistic.timestamp))
        .order_by(func.date(Statistic.timestamp).desc())
        .limit(days)
        .all()
    )

    return [
        {
            "date": str(r[0]),
            "total": int(r[1] or 0),
            "sleeping": int(r[2] or 0),
            "focus_rate": 1 - (r[2] / r[1]) if r[1] else 0.0,
        }
        for r in results
    ]


def get_stats_by_date(db: DBSession, user_id: Optional[int], days: int = 30) -> list[dict]:
    """Gộp số lượt gian lận theo từng ngày trong N ngày gần nhất.
    Điểm logic: chỉ lấy cột gian lận để vẽ biểu đồ theo ngày."""
    query = _join_user(
        db.query(
            func.date(Statistic.timestamp),
            func.sum(Statistic.sleeping_count),
        ),
        user_id,
    )

    results = (
        query.group_by(func.date(Statistic.timestamp))
        .order_by(func.date(Statistic.timestamp).desc())
        .limit(days)
        .all()
    )

    return [
        {"date": str(r[0]), "value": int(r[1] or 0)}
        for r in results
    ]


def get_weekly_stats(db: DBSession, user_id: Optional[int], weeks: int = 4) -> list[dict]:
    """Gộp số liệu theo tuần ISO trong N tuần gần nhất.
    Điểm logic: nhóm theo chuỗi năm-tuần ISO; tỉ lệ sạch lấy trung bình rồi làm tròn 3 chữ số."""
    week_expr = func.to_char(Statistic.timestamp, 'YYYY-"W"IW')

    query = _join_user(
        db.query(
            week_expr.label("week"),
            func.sum(Statistic.total_students),
            func.avg(Statistic.focus_rate),
        ),
        user_id,
    )

    results = (
        query.group_by(week_expr).order_by(week_expr.desc()).limit(weeks).all()
    )

    return [
        {
            "week": r[0],
            "total": int(r[1] or 0),
            "focus_rate": round(float(r[2]) if r[2] else 0.0, 3),
        }
        for r in results
    ]


def get_stats_summary(db: DBSession, user_id: Optional[int]) -> dict:
    """Trả thống kê tổng toàn cục.
    Điểm logic: gom toàn bộ bản ghi; giá trị rỗng coi như 0 để không vỡ phép tính."""
    query = _join_user(
        db.query(
            func.count(Statistic.statistic_id),
            func.sum(Statistic.total_students),
            func.avg(Statistic.focus_rate),
            func.sum(Statistic.sleeping_count),
        ),
        user_id,
    )

    result = query.first()

    return {
        "total_records": int(result[0] or 0),
        "total_students": int(result[1] or 0),
        "avg_focus_rate": round(float(result[2]) if result[2] else 0.0, 3),
        "sleeping_alerts": int(result[3] or 0),
    }
