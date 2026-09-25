"""Quản lý frame ảnh cắt từ camera trong ca thi.
Logic chính: dùng flush để lấy frame_id trước commit cho pipeline AI ghi kết quả ngay.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session as DBSession

from models.frame import Frame


def create_frame(db: DBSession, image_path: str, session_id: int) -> Frame:
    """Tạo bản ghi frame. Dùng flush để có ID trước commit cho bước AI phía sau."""
    frame = Frame(
        image_path=image_path,
        extracted_at=datetime.now(timezone.utc),
        session_id=session_id,
    )
    db.add(frame)
    db.flush()
    return frame


def get_frame_by_id(db: DBSession, frame_id: int) -> Optional[Frame]:
    """Lấy một frame theo khóa chính."""
    return db.query(Frame).filter(Frame.frame_id == frame_id).first()


def get_frames_by_session(
    db: DBSession,
    session_id: int,
    skip: int = 0,
    limit: int = 50,
) -> list[Frame]:
    """Lấy frame của một ca thi. Sắp mới nhất trước, có phân trang."""
    return (
        db.query(Frame)
        .filter(Frame.session_id == session_id)
        .order_by(Frame.extracted_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
