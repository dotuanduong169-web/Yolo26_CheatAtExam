"""Bảng Thí sinh (tbl_thi_sinh). Danh sách dự thi do giám thị nhập theo ca thi."""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, Column, ForeignKey, String, TIMESTAMP, UniqueConstraint
from sqlalchemy.orm import relationship

from database.database import Base


class Candidate(Base):
    __tablename__ = "tbl_thi_sinh"

    __table_args__ = (
        UniqueConstraint("SBD", "FK_MaPhienGiamSat", name="uq_candidate_sbd_session"),
    )

    PK_MaThiSinh = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    SBD = Column(String(50), nullable=False, index=True)
    HoTen = Column(String(255), nullable=False)
    Lop = Column(String(100), nullable=True)
    FK_MaPhienGiamSat = Column(
        BigInteger,
        ForeignKey("tbl_monitoring_sessions.PK_MaPhienGiamSat", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ThoiGianTao = Column(TIMESTAMP, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Quan hệ
    exam_session = relationship("MonitoringSession", back_populates="candidates", foreign_keys=[FK_MaPhienGiamSat])
    sub_sessions = relationship(
        "MonitoringSession",
        back_populates="candidate",
        foreign_keys="MonitoringSession.FK_MaThiSinh",
        cascade="all, delete",
    )

    def __repr__(self) -> str:
        return f"<Candidate(id={self.PK_MaThiSinh}, sbd={self.SBD!r})>"
