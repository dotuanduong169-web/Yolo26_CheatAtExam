"""Bảng snapshot ảnh (tbl_snapshot) và ảnh dẫn xuất (tbl_snapshot_processed).

Luồng dữ liệu:
    JPEG gốc -> images/raw/... + tbl_snapshot (cho_xu_ly)
              -> chuẩn hoá, thumbnail, annotated
              -> images/processed/... + tbl_snapshot_processed
              -> dashboard đọc ảnh dẫn xuất để hiển thị.

Ảnh nhị phân KHÔNG lưu trong PostgreSQL; DB chỉ lưu đường dẫn và metadata.
"""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, CheckConstraint, Column, ForeignKey, Integer, String, TIMESTAMP, Text
from sqlalchemy.orm import relationship

from database.database import Base


class Snapshot(Base):
    __tablename__ = "tbl_snapshot"

    __table_args__ = (
        CheckConstraint(
            "\"TrangThaiXuLy\" IN ('cho_xu_ly', 'dang_xu_ly', 'xong', 'loi')",
            name="ck_snapshot_trangthai",
        ),
    )

    PK_MaSnapshot = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    FK_MaPhienGiamSat = Column(
        BigInteger,
        ForeignKey("tbl_monitoring_sessions.PK_MaPhienGiamSat", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    FK_MaStream = Column(
        BigInteger,
        ForeignKey("tbl_camera_stream.PK_MaStream", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    VaiTroCamera = Column(String(20), nullable=False, default="front", index=True)
    ThoiGianChup = Column(TIMESTAMP, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    DuongDanGoc = Column(String(500), nullable=False)
    Hash = Column(String(64), nullable=True, index=True)
    KichThuocGoc = Column(Integer, nullable=True)
    Width = Column(Integer, nullable=True)
    Height = Column(Integer, nullable=True)
    TrangThaiXuLy = Column(String(20), nullable=False, default="cho_xu_ly", index=True)
    GhiChu = Column(Text, nullable=True)
    ThoiGianTao = Column(TIMESTAMP, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Quan hệ
    session = relationship("MonitoringSession", back_populates="snapshots")
    stream = relationship("CameraStream", back_populates="snapshots")
    processed = relationship(
        "SnapshotProcessed",
        back_populates="snapshot",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Snapshot(id={self.PK_MaSnapshot}, session={self.FK_MaPhienGiamSat}, role={self.VaiTroCamera!r})>"


class SnapshotProcessed(Base):
    __tablename__ = "tbl_snapshot_processed"

    __table_args__ = (
        CheckConstraint(
            "\"LoaiAnh\" IN ('normalized', 'thumbnail', 'annotated')",
            name="ck_snapshot_processed_loaianh",
        ),
    )

    PK_MaAnh = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    FK_MaSnapshot = Column(
        BigInteger,
        ForeignKey("tbl_snapshot.PK_MaSnapshot", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    LoaiAnh = Column(String(20), nullable=False)
    DuongDanTep = Column(String(500), nullable=False)
    Width = Column(Integer, nullable=True)
    Height = Column(Integer, nullable=True)
    KichThuoc = Column(Integer, nullable=True)
    ThoiGianTao = Column(TIMESTAMP, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Quan hệ
    snapshot = relationship("Snapshot", back_populates="processed")

    def __repr__(self) -> str:
        return f"<SnapshotProcessed(id={self.PK_MaAnh}, snapshot={self.FK_MaSnapshot}, type={self.LoaiAnh!r})>"
