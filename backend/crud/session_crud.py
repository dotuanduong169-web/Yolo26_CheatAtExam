"""Quản lý ca thi (session) gắn với camera và phòng thi.
Logic chính: đếm frame bằng outerjoin và group by trong một truy vấn, xóa cascade từ file ảnh tới bản ghi.
"""

import os
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from core.logger import get_logger
from models.ai_result import AIResult
from models.frame import Frame
from models.session import Session as SessionModel
from models.statistic import Statistic

logger = get_logger(__name__)


def create_session(
    db: DBSession,
    user_id: int,
    class_id: str,
    camera_url: str,
) -> SessionModel:
    """Tạo ca thi mới. Ghi start_time theo giờ UTC rồi commit để lấy ID ngay."""
    session = SessionModel(
        class_id=class_id,
        start_time=datetime.now(timezone.utc),
        camera_url=camera_url,
        user_id=user_id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def end_session(db: DBSession, session_id: int) -> None:
    """Kết thúc ca thi. Ghi end_time UTC, bỏ qua nếu session không tồn tại."""
    session = (
        db.query(SessionModel)
        .filter(SessionModel.session_id == session_id)
        .first()
    )
    if session:
        session.end_time = datetime.now(timezone.utc)
        db.commit()


def get_session_by_id(
    db: DBSession,
    session_id: int,
) -> Optional[SessionModel]:
    """Lấy một session theo khóa chính."""
    return (
        db.query(SessionModel)
        .filter(SessionModel.session_id == session_id)
        .first()
    )


def get_sessions_by_user(
    db: DBSession,
    user_id: int,
    skip: int = 0,
    limit: int = 20,
) -> list[SessionModel]:
    """Lấy session của một người dùng. Sắp mới nhất trước, có phân trang."""
    return (
        db.query(SessionModel)
        .filter(SessionModel.user_id == user_id)
        .order_by(SessionModel.start_time.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_sessions_with_frame_count(
    db: DBSession,
    user_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
) -> list[Any]:
    """Lấy session kèm số frame. Gom trong một truy vấn outerjoin và group by để chống N+1."""
    query = (
        db.query(
            SessionModel.session_id,
            SessionModel.class_id,
            SessionModel.start_time,
            func.count(Frame.frame_id).label("frame_count"),
        )
        .outerjoin(Frame, Frame.session_id == SessionModel.session_id)
    )

    if user_id is not None:
        query = query.filter(SessionModel.user_id == user_id)

    if search:
        query = query.filter(SessionModel.class_id.ilike(f"%{search}%"))

    return (
        query
        .group_by(SessionModel.session_id)
        .order_by(SessionModel.start_time.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_session_count_by_user(db: DBSession, user_id: Optional[int] = None) -> int:
    """Đếm tổng session. Bỏ lọc user khi user_id là None để admin xem toàn hệ thống."""
    query = db.query(func.count(SessionModel.session_id))
    if user_id is not None:
        query = query.filter(SessionModel.user_id == user_id)
    return query.scalar() or 0


def get_monthly_session_count_by_user(db: DBSession, user_id: Optional[int] = None) -> int:
    """Đếm session từ ngày 1 đầu tháng hiện tại (mốc UTC). Lọc theo user trừ khi là admin."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    query = db.query(func.count(SessionModel.session_id)).filter(
        SessionModel.start_time >= month_start
    )
    if user_id is not None:
        query = query.filter(SessionModel.user_id == user_id)

    return query.scalar() or 0


def delete_session_cascade(
    db: DBSession,
    session_id: int,
    user_id: int,
    base_dir: str,
) -> bool:
    """Xóa session và toàn bộ dữ liệu liên quan. Trả về False nếu không tìm thấy hoặc không thuộc user.

    Thứ tự xóa: file ảnh trên đĩa rồi mới tới kết quả AI, thống kê, frame, session.
    """
    query = db.query(SessionModel).filter(SessionModel.session_id == session_id)

    if user_id is not None:
        query = query.filter(SessionModel.user_id == user_id)

    session = query.first()
    if not session:
        return False

    # Xóa file ảnh khỏi đĩa, lỗi từng file chỉ ghi log rồi bỏ qua
    frames = db.query(Frame).filter(Frame.session_id == session_id).all()
    for frame in frames:
        if frame.image_path:
            full_path = os.path.join(base_dir, frame.image_path)
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                except OSError as exc:
                    logger.warning(f"Failed to delete file {full_path}: {exc}")

    # Xóa bản ghi liên quan trước khi xóa session
    frame_ids = db.query(Frame.frame_id).filter(Frame.session_id == session_id)

    db.query(AIResult).filter(
        AIResult.frame_id.in_(frame_ids)
    ).delete(synchronize_session=False)

    db.query(Statistic).filter(
        Statistic.session_id == session_id
    ).delete(synchronize_session=False)

    db.query(Frame).filter(
        Frame.session_id == session_id
    ).delete(synchronize_session=False)

    db.delete(session)
    db.commit()
    return True
