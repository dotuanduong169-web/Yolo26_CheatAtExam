"""Quản lý snapshot thống kê theo ca thi.
Logic chính: sleeping_count là số vật gian lận (Cheat_Paper và cellphone), focus_rate là tỉ lệ bài sạch.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session as DBSession

from models.ai_result import AIResult
from models.statistic import Statistic
from ai_model.ai_pipeline import is_cheat_label
from utils.label_utils import get_final_label


def create_statistics(db: DBSession, data: dict, session_id: int) -> Statistic:
    """Tạo snapshot thống kê. Dùng flush để có ID trước commit cho luồng lưu frame."""
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
    """Lấy toàn bộ thống kê của một ca thi. Sắp mới nhất trước."""
    return (
        db.query(Statistic)
        .filter(Statistic.session_id == session_id)
        .order_by(Statistic.timestamp.desc())
        .all()
    )


def recalculate_statistics_for_frame(
    db: DBSession,
    session_id: int,
    frame_id: int,
) -> Optional[Statistic]:
    """Tính lại thống kê sau khi người dùng sửa nhãn để tổng hợp cấp session đồng bộ.

    Nhãn hiệu lực lấy qua get_final_label nên user_label luôn ưu tiên hơn ai_label,
    nhãn gian lận gồm Cheat_Paper và cellphone, ghép bản ghi thống kê với frame theo
    vị trí vì hai bảng tạo cặp cùng lúc.
    """
    from models.frame import Frame

    # Lấy toàn bộ kết quả của frame này
    results = db.query(AIResult).filter(AIResult.frame_id == frame_id).all()
    if not results:
        return None

    total = len(results)
    sleeping = sum(
        1 for r in results if is_cheat_label(get_final_label(r) or "")
    )
    focus_rate = 1 - (sleeping / total) if total else 1.0

    # Tìm frame để lấy thời điểm trích xuất
    frame = db.query(Frame).filter(Frame.frame_id == frame_id).first()
    if not frame:
        return None

    # Tìm bản ghi thống kê gần nhất vì thống kê và frame tạo cặp cùng lúc trong _save_snapshot
    stats = (
        db.query(Statistic)
        .filter(Statistic.session_id == session_id)
        .order_by(Statistic.timestamp.desc())
        .all()
    )

    if not stats:
        return None

    # Ghép theo vị trí: frame và thống kê tạo cặp nên sắp cùng thứ tự rồi đối chiếu chỉ số
    frames = (
        db.query(Frame)
        .filter(Frame.session_id == session_id)
        .order_by(Frame.extracted_at.desc())
        .all()
    )

    # Tìm vị trí của frame trong danh sách
    target_idx = None
    for idx, f in enumerate(frames):
        if f.frame_id == frame_id:
            target_idx = idx
            break

    if target_idx is not None and target_idx < len(stats):
        stat = stats[target_idx]
        stat.total_students = total
        stat.sleeping_count = sleeping
        stat.focus_rate = focus_rate
        db.commit()
        db.refresh(stat)
        return stat

    return None
