"""Bảng nhật ký quan sát theo tick (tbl_candidate_timeline).

Mỗi bản ghi là một mốc quan sát của một luồng camera:
- tick có cảnh báo: ghi mọi lần để không bỏ sót thay đổi;
- tick chuyển trạng thái (bắt đầu/kết thúc cảnh báo): ghi để timeline liên tục;
- heartbeat khi sạch: ghi thưa theo TIMELINE_HEARTBEAT_SECONDS.

Ảnh minh chứng là thumbnail nhỏ (tbl_snapshot / tbl_snapshot_processed), không lưu
raw cho mọi tick để tránh phình dung lượng. Sự kiện nghiệp vụ vẫn nằm ở
tbl_detected_events và được liên kết qua FK_MaSuKien khi có.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    TIMESTAMP,
)
from sqlalchemy.orm import relationship

from database.database import Base


class CandidateTimeline(Base):
    """Một mốc quan sát 2,5 giây (hoặc tick kế tiếp) của thí sinh."""

    __tablename__ = "tbl_candidate_timeline"

    __table_args__ = (
        Index("ix_timeline_candidate_time", "FK_MaThiSinh", "ThoiDiem"),
        Index("ix_timeline_session_time", "FK_MaPhienGiamSat", "ThoiDiem"),
        Index("ix_timeline_alert_time", "CoCanhBao", "ThoiDiem"),
    )

    PK_MaDong = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    FK_MaPhienGiamSat = Column(
        BigInteger,
        ForeignKey("tbl_monitoring_sessions.PK_MaPhienGiamSat", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    FK_MaThiSinh = Column(
        BigInteger,
        ForeignKey("tbl_thi_sinh.PK_MaThiSinh", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    ThoiDiem = Column(TIMESTAMP, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    TickIndex = Column(Integer, nullable=False, default=0)
    CoCanhBao = Column(Boolean, nullable=False, default=False, index=True)
    DanhSachPhatHien = Column(JSON, nullable=True)
    FK_MaSnapshot = Column(
        BigInteger,
        ForeignKey("tbl_snapshot.PK_MaSnapshot", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    FK_MaSuKien = Column(
        BigInteger,
        ForeignKey("tbl_detected_events.PK_MaSuKien", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    VaiTroCamera = Column(String(20), nullable=False, default="front", index=True)
    NguonAnh = Column(String(20), nullable=False, default="thumbnail")
    # Độ trễ từ lúc server nhận frame đến lúc ghi xong timeline (ms).
    DoTreMs = Column(Integer, nullable=True)
    ThoiGianTao = Column(TIMESTAMP, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Quan hệ
    session = relationship("MonitoringSession")
    candidate = relationship("Candidate")
    snapshot = relationship("Snapshot")
    event = relationship("DetectedEvent")

    def __repr__(self) -> str:
        return (
            f"<CandidateTimeline(id={self.PK_MaDong}, session={self.FK_MaPhienGiamSat}, "
            f"alert={self.CoCanhBao})>"
        )
