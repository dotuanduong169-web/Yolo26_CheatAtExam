"""Bảng Thiết bị biên (tbl_edgedevice). Camera/đầu ghi RTSP gắn với phiên giám sát."""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, CheckConstraint, Column, String, TIMESTAMP
from sqlalchemy.orm import relationship

from database.database import Base


class EdgeDevice(Base):
    __tablename__ = "tbl_edgedevice"

    __table_args__ = (
        CheckConstraint(
            "\"TrangThai\" IN ('san_sang', 'dang_chay', 'loi', 'tat')",
            name="ck_device_trangthai",
        ),
    )

    PK_MaThietBi = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    TenThietBi = Column(String(255), nullable=False)
    DuongDanRTSP = Column(String(255), nullable=False)
    MoTaViTri = Column(String(255), nullable=True)
    TrangThai = Column(String(50), nullable=False, default="san_sang")
    ThoiGianTao = Column(TIMESTAMP, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Quan hệ
    sessions = relationship("MonitoringSession", back_populates="device")

    def __repr__(self) -> str:
        return f"<EdgeDevice(id={self.PK_MaThietBi}, name={self.TenThietBi!r})>"
