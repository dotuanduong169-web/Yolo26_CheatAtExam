"""Quản lý snapshot thống kê theo phiên.
Logic chính: mỗi snapshot ghi tổng phát hiện trong kỳ; key giữ tương thích API cũ.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session as DBSession

from models.statistic import Statistic


def create_statistics(db: DBSession, data: dict, session_id: int) -> Statistic:
    """Tạo snapshot thống kê. Dùng flush để có ID trước commit cho luồng lưu sự kiện."""
    stat = Statistic(
        timestamp=datetime.now(timezone.utc),
        total_students=data["total"],
        sleeping_count=data["sleeping"],
        focus_rate=data["focus_rate"],
        session_id=session_id,
    )
    db.add(stat)
    db.flush()
    return stat


def get_stats_by_session(db: DBSession, session_id: int) -> list[Statistic]:
    """Lấy toàn bộ thống kê của một phiên. Sắp mới nhất trước."""
    return (
        db.query(Statistic)
        .filter(Statistic.session_id == session_id)
        .order_by(Statistic.timestamp.desc())
        .all()
    )
