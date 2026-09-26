"""Bảng Phiên giám sát (tbl_monitoring_sessions). Thuộc về một user và một thiết bị biên."""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, CheckConstraint, Column, ForeignKey, String, TIMESTAMP
from sqlalchemy.orm import relationship

from database.database import Base


class MonitoringSession(Base):
    __tablename__ = "tbl_monitoring_sessions"

    __table_args__ = (
        CheckConstraint(
            "\"TrangThai\" IN ('dang_giam_sat', 'ket_thuc')",
            name="ck_session_trangthai",
        ),
    )

    PK_MaPhienGiamSat = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    ThoiGianBatDau = Column(TIMESTAMP, nullable=False, default=lambda: datetime.now(timezone.utc))
    ThoiGianKetThuc = Column(TIMESTAMP, nullable=True)
    TrangThai = Column(String(255), nullable=False, default="dang_giam_sat")
    PhongThi = Column(String(50), nullable=True)
    MonThi = Column(String(255), nullable=True)
    ThoiGianTao = Column(TIMESTAMP, nullable=False, default=lambda: datetime.now(timezone.utc))
    FK_MaNguoiDung = Column(BigInteger, ForeignKey("tbl_user.PK_MaNguoiDung", ondelete="SET NULL"), nullable=False)
    FK_MaThietBi = Column(BigInteger, ForeignKey("tbl_edgedevice.PK_MaThietBi", ondelete="RESTRICT"), nullable=False)

    # Quan hệ
    user = relationship("User", back_populates="sessions")
    device = relationship("EdgeDevice", back_populates="sessions")
    events = relationship("DetectedEvent", back_populates="session", cascade="all, delete")
    statistics = relationship("Statistic", back_populates="session", cascade="all, delete")

    def __repr__(self) -> str:
        return f"<MonitoringSession(id={self.PK_MaPhienGiamSat}, room={self.PhongThi!r})>"
