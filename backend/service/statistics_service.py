"""Tổng hợp thống kê gian lận: theo ngày, theo tuần ISO, theo khoảng ngày, toàn cục.
Luồng chính: lọc theo người dùng qua phiên giám sát → gom nhóm theo mốc thời gian."""

from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from models.detected_event import DetectedEvent
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


def _filter_events_user(query, user_id: Optional[int]):
    """Lọc sự kiện theo người sở hữu phiên thi."""
    if user_id is None:
        return query
    return query.join(
        MonitoringSession, DetectedEvent.FK_MaPhienGiamSat == MonitoringSession.PK_MaPhienGiamSat
    ).filter(MonitoringSession.FK_MaNguoiDung == user_id)


def get_daily_stats(db: DBSession, user_id: Optional[int], days: int = 30) -> list[dict]:
    """Gộp số liệu theo từng ngày trong N ngày gần nhất từ sự kiện vi phạm thực tế."""
    # Ưu tiên lấy từ bảng DetectedEvent thực tế
    q_events = _filter_events_user(
        db.query(
            func.date(DetectedEvent.ThoiGianPhatHien).label("d"),
            func.count(DetectedEvent.PK_MaSuKien).label("cnt"),
        ),
        user_id,
    ).group_by(func.date(DetectedEvent.ThoiGianPhatHien)).order_by(func.date(DetectedEvent.ThoiGianPhatHien).desc()).limit(days)

    res_events = q_events.all()
    if res_events:
        return [
            {
                "date": str(r[0]),
                "total": int(r[1] or 0),
                "sleeping": int(r[1] or 0),
                "focus_rate": max(0.0, 1.0 - (int(r[1] or 0) * 0.05)),
            }
            for r in res_events
        ]

    # Fallback bảng Statistic
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
    """Gộp số lượt gian lận theo từng ngày trong N ngày gần nhất."""
    # Lấy từ DetectedEvent thực tế
    q_events = _filter_events_user(
        db.query(
            func.date(DetectedEvent.ThoiGianPhatHien).label("d"),
            func.count(DetectedEvent.PK_MaSuKien).label("cnt"),
        ),
        user_id,
    ).group_by(func.date(DetectedEvent.ThoiGianPhatHien)).order_by(func.date(DetectedEvent.ThoiGianPhatHien).desc()).limit(days)

    res_events = q_events.all()
    if res_events:
        return [{"date": str(r[0]), "value": int(r[1] or 0)} for r in res_events]

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
    return [{"date": str(r[0]), "value": int(r[1] or 0)} for r in results]


def get_weekly_stats(db: DBSession, user_id: Optional[int], weeks: int = 4) -> list[dict]:
    """Gộp số liệu theo tuần ISO trong N tuần gần nhất."""
    week_expr = func.to_char(Statistic.timestamp, 'YYYY-"W"IW')
    query = _join_user(
        db.query(
            week_expr.label("week"),
            func.sum(Statistic.total_students),
            func.avg(Statistic.focus_rate),
        ),
        user_id,
    )
    results = query.group_by(week_expr).order_by(week_expr.desc()).limit(weeks).all()
    return [
        {
            "week": r[0],
            "total": int(r[1] or 0),
            "focus_rate": round(float(r[2]) if r[2] else 0.0, 3),
        }
        for r in results
    ]


def get_behavior_distribution(db: DBSession, user_id: Optional[int] = None) -> list[dict]:
    """Tổng hợp phân bố hành vi gian lận thực tế từ cơ sở dữ liệu."""
    label_map = {
        "Cheat_Paper": "Tài liệu giấy (Cheat_Paper)",
        "cellphone": "Điện thoại di động (cellphone)",
        "quay_dau": "Quay đầu bất thường (>45°)",
        "quay_sau": "Quay người về sau",
        "cui_xuong": "Cúi đầu nhìn xuống bàn",
    }
    q = _filter_events_user(
        db.query(
            DetectedEvent.LoaiHanhVi,
            func.count(DetectedEvent.PK_MaSuKien),
        ),
        user_id,
    ).group_by(DetectedEvent.LoaiHanhVi).all()

    total = sum(int(r[1] or 0) for r in q)
    if total == 0:
        return []

    distribution = []
    for r in q:
        beh = r[0]
        cnt = int(r[1] or 0)
        pct = round((cnt / total) * 100, 1)
        distribution.append({
            "behavior_code": beh,
            "behavior_name": label_map.get(beh, beh),
            "count": cnt,
            "percentage": pct,
        })
    return sorted(distribution, key=lambda x: x["count"], reverse=True)


def get_stats_summary(db: DBSession, user_id: Optional[int]) -> dict:
    """Trả thống kê tổng toàn cục tính từ dữ liệu thực tế."""
    # 1. Đếm tổng sự kiện gian lận thực tế
    q_ev = _filter_events_user(db.query(func.count(DetectedEvent.PK_MaSuKien)), user_id)
    total_detected_events = q_ev.scalar() or 0

    # 2. Đếm tổng số ca thi thực tế
    q_sess = db.query(func.count(MonitoringSession.PK_MaPhienGiamSat))
    if user_id is not None:
        q_sess = q_sess.filter(MonitoringSession.FK_MaNguoiDung == user_id)
    total_sessions = q_sess.scalar() or 0

    # 3. Tính tỷ lệ phòng sạch (ca thi không có vi phạm hoặc tỷ lệ sạch)
    clean_sessions = 0
    if total_sessions > 0:
        q_clean = db.query(MonitoringSession.PK_MaPhienGiamSat).outerjoin(
            DetectedEvent, DetectedEvent.FK_MaPhienGiamSat == MonitoringSession.PK_MaPhienGiamSat
        )
        if user_id is not None:
            q_clean = q_clean.filter(MonitoringSession.FK_MaNguoiDung == user_id)
        q_clean = q_clean.group_by(MonitoringSession.PK_MaPhienGiamSat).having(
            func.count(DetectedEvent.PK_MaSuKien) == 0
        )
        clean_sessions = q_clean.count()
        clean_rate = round((clean_sessions / total_sessions) * 100, 1)
    else:
        clean_rate = 100.0

    # 4. Tìm hành vi phổ biến nhất
    dist = get_behavior_distribution(db, user_id)
    most_common = dist[0]["behavior_name"] if dist else "Chưa có vi phạm"

    return {
        "total_records": total_sessions,
        "total_students": total_sessions,
        "total_sessions": total_sessions,
        "total_cheats": total_detected_events,
        "sleeping_alerts": total_detected_events,  # Tương thích ngược key cũ
        "avg_focus_rate": round(clean_rate / 100.0, 3),
        "clean_rate": clean_rate,
        "most_common_behavior": most_common,
    }
