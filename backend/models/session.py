"""Phiên ghi hình camera của lớp thi. Logic: thuộc về một user, xóa thì kéo theo frame và thống kê."""

from datetime import datetime, timezone

from sqlalchemy import Column, ForeignKey, Integer, String, TIMESTAMP
from sqlalchemy.orm import relationship

from database.database import Base


class Session(Base):
    __tablename__ = "sessions"

    session_id = Column(Integer, primary_key=True, index=True)
    class_id = Column(String(100), nullable=False)
    start_time = Column(TIMESTAMP, default=lambda: datetime.now(timezone.utc))
    end_time = Column(TIMESTAMP, nullable=True)
    camera_url = Column(String)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"))

    # Quan hệ
    user = relationship("User", back_populates="sessions")
    frames = relationship("Frame", back_populates="session", cascade="all, delete")
    statistics = relationship("Statistic", back_populates="session", cascade="all, delete")

    def __repr__(self) -> str:
        """Trả chuỗi nhận diện phiên theo id và mã lớp."""
        return f"<Session(id={self.session_id}, class={self.class_id!r})>"