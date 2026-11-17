"""Bảng Luồng camera (tbl_camera_stream).

Mỗi phiên thí sinh có thể có nhiều luồng camera (webcam trước + điện thoại phụ).
Token, trạng thái và thời điểm nhận frame được quản lý theo từng luồng thay vì
một token duy nhất trên phiên như trước đây.
"""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, CheckConstraint, Column, ForeignKey, String, TIMESTAMP, UniqueConstraint
from sqlalchemy.orm import relationship

from database.database import Base


class CameraStream(Base):
    __tablename__ = "tbl_camera_stream"

    __table_args__ = (
        CheckConstraint("\"VaiTro\" IN ('front', 'side')", name="ck_stream_vaitro"),
        CheckConstraint(
            "\"TrangThai\" IN ('dang_hoat_dong', 'mat_ket_noi', 'ket_thuc')",
            name="ck_stream_trangthai",
        ),
        UniqueConstraint("FK_MaPhienGiamSat", "VaiTro", name="uq_stream_session_vaitro"),
    )

    PK_MaStream = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    FK_MaPhienGiamSat = Column(
        BigInteger,
        ForeignKey("tbl_monitoring_sessions.PK_MaPhienGiamSat", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    VaiTro = Column(String(20), nullable=False, default="front")
    Token = Column(String(255), nullable=True, unique=True, index=True)
    TrangThai = Column(String(20), nullable=False, default="dang_hoat_dong")
    LanCuoiNhan = Column(TIMESTAMP, nullable=True)
    ThoiGianTao = Column(TIMESTAMP, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Quan hệ
    session = relationship("MonitoringSession", back_populates="streams")
    # Xoá luồng chỉ ngắt liên kết (FK SET NULL), KHÔNG xoá snapshot của phiên.
    snapshots = relationship("Snapshot", back_populates="stream", passive_deletes=True)

    def __repr__(self) -> str:
        return f"<CameraStream(id={self.PK_MaStream}, session={self.FK_MaPhienGiamSat}, role={self.VaiTro!r})>"
