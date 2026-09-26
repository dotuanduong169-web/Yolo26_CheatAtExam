"""Bảng Sự kiện phát hiện (tbl_detected_events). Chỉ lưu hành vi gian lận đã debounce."""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, CheckConstraint, Column, Float, ForeignKey, JSON, String, TIMESTAMP
from sqlalchemy.orm import relationship

from database.database import Base


class DetectedEvent(Base):
    __tablename__ = "tbl_detected_events"

    __table_args__ = (
        CheckConstraint("\"LoaiHanhVi\" IN ('Cheat_Paper', 'cellphone')", name="ck_event_loai"),
        CheckConstraint('"DoTinCay" >= 0 AND "DoTinCay" <= 1', name="ck_event_dotincay"),
        CheckConstraint(
            "\"TrangThaiKiemTra\" IN ('cho_kiem_tra', 'dung', 'sai')",
            name="ck_event_trangthaikiemtra",
        ),
    )

    PK_MaSuKien = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    LoaiHanhVi = Column(String(255), nullable=False)
    NhanAI = Column(String(100), nullable=False)
    NhanNguoiDung = Column(String(100), nullable=True)
    ToaDo = Column(JSON, nullable=False)
    DoTinCay = Column(Float, nullable=False)
    ThoiGianPhatHien = Column(TIMESTAMP, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    TrangThaiKiemTra = Column(String(255), nullable=True, default="cho_kiem_tra", index=True)
    FK_MaNguoiKiemTra = Column(BigInteger, ForeignKey("tbl_user.PK_MaNguoiDung", ondelete="SET NULL"), nullable=True)
    ThoiGianKiemTra = Column(TIMESTAMP, nullable=True)
    FK_MaPhienGiamSat = Column(
        BigInteger,
        ForeignKey("tbl_monitoring_sessions.PK_MaPhienGiamSat", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ThoiGianTao = Column(TIMESTAMP, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Quan hệ
    session = relationship("MonitoringSession", back_populates="events")
    evidences = relationship("Evidence", back_populates="event", cascade="all, delete")

    def __repr__(self) -> str:
        return f"<DetectedEvent(id={self.PK_MaSuKien}, behavior={self.LoaiHanhVi!r})>"
