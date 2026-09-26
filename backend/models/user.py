"""Bảng Người dùng (tbl_user). Một user sở hữu nhiều phiên giám sát."""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, CheckConstraint, Column, String, TIMESTAMP
from sqlalchemy.orm import relationship

from database.database import Base


class User(Base):
    __tablename__ = "tbl_user"

    __table_args__ = (
        CheckConstraint("\"VaiTro\" IN ('admin', 'teacher')", name="ck_user_vaitro"),
        CheckConstraint("\"TrangThai\" IN ('hoat_dong', 'khoa')", name="ck_user_trangthai"),
    )

    PK_MaNguoiDung = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    TenDangNhap = Column(String(255), unique=True, nullable=False, index=True)
    MatKhau = Column(String(255), nullable=False)
    HoVaTen = Column(String(255), nullable=False)
    VaiTro = Column(String(50), nullable=False, default="teacher")
    TrangThai = Column(String(255), nullable=False, default="hoat_dong")
    ThoiGianTao = Column(TIMESTAMP, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Quan hệ
    sessions = relationship("MonitoringSession", back_populates="user")

    def __repr__(self) -> str:
        return f"<User(id={self.PK_MaNguoiDung}, username={self.TenDangNhap!r})>"
