"""Thống kê tổng hợp từng thời điểm. Logic: gắn với một phiên để tính sĩ số và tỉ lệ tập trung."""

from datetime import datetime, timezone

from sqlalchemy import Column, Float, ForeignKey, Integer, TIMESTAMP
from sqlalchemy.orm import relationship

from database.database import Base


class Statistic(Base):
    __tablename__ = "statistics"

    statistic_id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(TIMESTAMP, default=lambda: datetime.now(timezone.utc))
    total_students = Column(Integer, nullable=False)
    sleeping_count = Column(Integer, nullable=False)
    focus_rate = Column(Float, nullable=False)
    session_id = Column(Integer, ForeignKey("sessions.session_id", ondelete="CASCADE"))

    # Quan hệ
    session = relationship("Session", back_populates="statistics")

    def __repr__(self) -> str:
        """Trả chuỗi nhận diện thống kê theo id và tỉ lệ tập trung."""
        return f"<Statistic(id={self.statistic_id}, focus={self.focus_rate:.1%})>"