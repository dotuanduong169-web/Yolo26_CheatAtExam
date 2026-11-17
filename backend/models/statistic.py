"""Bảng Thống kê legacy (statistics).

Bảng này KHÔNG còn được đăng ký trong ``models/__init__`` và không được ghi dữ
liệu: số liệu thống kê hiện được tổng hợp trực tiếp từ ``tbl_detected_events``.
Giữ model để tương thích với DB cũ, không dùng relationship để tránh lỗi mapper
khi module không được import.
"""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, Column, Float, ForeignKey, Integer, TIMESTAMP

from database.database import Base


class Statistic(Base):
    __tablename__ = "statistics"

    statistic_id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(TIMESTAMP, default=lambda: datetime.now(timezone.utc))
    total_students = Column(Integer, nullable=False)
    sleeping_count = Column(Integer, nullable=False)
    focus_rate = Column(Float, nullable=False)
    session_id = Column(
        BigInteger,
        ForeignKey("tbl_monitoring_sessions.PK_MaPhienGiamSat", ondelete="CASCADE"),
    )

    def __repr__(self) -> str:
        """Trả chuỗi nhận diện thống kê theo id và tỉ lệ tập trung."""
        return f"<Statistic(id={self.statistic_id}, focus={self.focus_rate:.1%})>"