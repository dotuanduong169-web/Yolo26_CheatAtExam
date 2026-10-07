"""Quản lý thí sinh: nhập danh sách theo ca, tìm theo SBD, mở phiên con.
Logic chính: SBD duy nhất trong một ca; join idempotent (vào lại trả phiên đang mở).
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from core.logger import get_logger
from models.candidate import Candidate
from models.detected_event import DetectedEvent
from models.monitoring_session import MonitoringSession

logger = get_logger(__name__)


def import_candidates(
    db: DBSession, session_id: int, items: list[dict]
) -> tuple[list[Candidate], list[str]]:
    """Nhập danh sách thí sinh cho ca thi. SBD trùng trong ca thì cập nhật họ tên/lớp.
    Trả về (danh sách đã lưu, SBD trùng lặp)."""
    seen: set[str] = set()
    duplicates: list[str] = []
    saved: list[Candidate] = []

    for item in items:
        sbd = str(item.get("SBD", "")).strip()
        if not sbd:
            continue
        if sbd in seen:
            duplicates.append(sbd)
            continue
        seen.add(sbd)

        existing = (
            db.query(Candidate)
            .filter(
                Candidate.FK_MaPhienGiamSat == session_id,
                Candidate.SBD == sbd,
            )
            .first()
        )
        if existing:
            existing.HoTen = str(item.get("HoTen", "")).strip() or existing.HoTen
            if item.get("Lop") is not None:
                existing.Lop = str(item.get("Lop")).strip() or None
            saved.append(existing)
        else:
            saved.append(
                Candidate(
                    SBD=sbd,
                    HoTen=str(item.get("HoTen", "")).strip(),
                    Lop=str(item.get("Lop")).strip() or None
                    if item.get("Lop") is not None
                    else None,
                    FK_MaPhienGiamSat=session_id,
                )
            )
            db.add(saved[-1])

    db.commit()
    for c in saved:
        db.refresh(c)
    return saved, duplicates


def list_candidates(db: DBSession, session_id: int) -> list[Candidate]:
    """Liệt kê thí sinh của một ca thi theo SBD."""
    return (
        db.query(Candidate)
        .filter(Candidate.FK_MaPhienGiamSat == session_id)
        .order_by(Candidate.SBD)
        .all()
    )


def find_candidate_for_join(
    db: DBSession, sbd: str, session_id: Optional[int] = None
) -> Optional[Candidate]:
    """Tìm thí sinh theo SBD để vào thi.
    Điểm logic: ưu tiên ca đang mở (dang_giam_sat); không có thì ca mới nhất chứa SBD."""
    sbd = sbd.strip()
    query = db.query(Candidate).filter(Candidate.SBD == sbd)
    if session_id is not None:
        query = query.filter(Candidate.FK_MaPhienGiamSat == session_id)

    rows = (
        query.join(
            MonitoringSession,
            MonitoringSession.PK_MaPhienGiamSat == Candidate.FK_MaPhienGiamSat,
        )
        .order_by(
            (MonitoringSession.TrangThai == "dang_giam_sat").desc(),
            MonitoringSession.ThoiGianBatDau.desc(),
        )
        .all()
    )
    return rows[0] if rows else None


def get_open_sub_session(
    db: DBSession, candidate_id: int
) -> Optional[MonitoringSession]:
    """Phiên con đang mở của thí sinh (join idempotent)."""
    return (
        db.query(MonitoringSession)
        .filter(
            MonitoringSession.FK_MaThiSinh == candidate_id,
            MonitoringSession.TrangThai == "dang_giam_sat",
        )
        .order_by(MonitoringSession.ThoiGianBatDau.desc())
        .first()
    )


def create_sub_session(
    db: DBSession,
    user_id: int,
    candidate: Candidate,
) -> MonitoringSession:
    """Mở phiên con cho thí sinh: kế thừa phòng/môn từ ca thi, không gắn thiết bị biên."""
    exam = (
        db.query(MonitoringSession)
        .filter(MonitoringSession.PK_MaPhienGiamSat == candidate.FK_MaPhienGiamSat)
        .first()
    )
    session = MonitoringSession(
        ThoiGianBatDau=datetime.now(timezone.utc),
        PhongThi=exam.PhongThi if exam else None,
        MonThi=exam.MonThi if exam else None,
        FK_MaNguoiDung=user_id,
        FK_MaThietBi=None,
        FK_MaThiSinh=candidate.PK_MaThiSinh,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def latest_evidence_time(db: DBSession, session_id: int):
    """Thời điểm ảnh mới nhất của phiên con (cho lưới giám thị)."""
    from models.evidence import Evidence

    row = (
        db.query(Evidence.ThoiGianTao)
        .join(
            DetectedEvent,
            DetectedEvent.PK_MaSuKien == Evidence.FK_MaSuKien,
        )
        .filter(DetectedEvent.FK_MaPhienGiamSat == session_id)
        .order_by(Evidence.ThoiGianTao.desc())
        .first()
    )
    return row[0] if row else None


def count_unverified_by_candidate(db: DBSession, session_id: int) -> tuple[int, int]:
    """Đếm (tổng sự kiện, chờ kiểm tra) của một phiên con."""
    total = (
        db.query(func.count(DetectedEvent.PK_MaSuKien))
        .filter(DetectedEvent.FK_MaPhienGiamSat == session_id)
        .scalar()
        or 0
    )
    pending = (
        db.query(func.count(DetectedEvent.PK_MaSuKien))
        .filter(
            DetectedEvent.FK_MaPhienGiamSat == session_id,
            DetectedEvent.TrangThaiKiemTra == "cho_kiem_tra",
        )
        .scalar()
        or 0
    )
    return total, pending
