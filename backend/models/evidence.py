"""Bảng Bằng chứng (tbl_evidences). Ảnh/video minh chứng cho một sự kiện (nhiều sự kiện chung ảnh được)."""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, CheckConstraint, Column, ForeignKey, String, TIMESTAMP
from sqlalchemy.orm import relationship

from database.database import Base


class Evidence(Base):
    __tablename__ = "tbl_evidences"

    __table_args__ = (
        CheckConstraint("\"LoaiTep\" IN ('anh', 'video')", name="ck_evidence_loaitep"),
    )

    PK_MaBangChung = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    LoaiTep = Column(String(50), nullable=False)
    DuongDanTep = Column(String(255), nullable=False)
    FK_MaSuKien = Column(
        BigInteger,
        ForeignKey("tbl_detected_events.PK_MaSuKien", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ThoiGianTao = Column(TIMESTAMP, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Quan hệ
    event = relationship("DetectedEvent", back_populates="evidences")

    def __repr__(self) -> str:
        return f"<Evidence(id={self.PK_MaBangChung}, event={self.FK_MaSuKien})>"
