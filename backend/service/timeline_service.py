"""Truy vấn nhật ký quan sát theo tick và thống kê gắn thí sinh.

Luồng chính:
- ingest ghi tick vào tbl_candidate_timeline (mọi tick có cảnh báo + tick đổi
  trạng thái + heartbeat);
- API thống kê đọc timeline kèm Candidate, Snapshot, DetectedEvent để trả về
  đủ ảnh, thời gian, thí sinh, hành vi và trạng thái xác minh.
"""

from __future__ import annotations

import base64
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession, aliased, joinedload

from core.logger import get_logger
from database.database import SessionLocal
from models.candidate import Candidate
from models.detected_event import DetectedEvent
from models.evidence import Evidence
from models.monitoring_session import MonitoringSession
from models.snapshot import Snapshot
from models.timeline import CandidateTimeline

logger = get_logger(__name__)


def _clean_detections(results: list[dict] | None, limit: int = 30) -> list[dict]:
    """Chuẩn hoá detection thành JSON gọn, bỏ mask/field không cần."""
    cleaned: list[dict] = []
    for r in (results or [])[:limit]:
        try:
            cleaned.append(
                {
                    "label": str(r.get("label") or ""),
                    "confidence": round(float(r.get("confidence") or 0.0), 4),
                    "bbox": [round(float(v), 1) for v in (r.get("bbox") or [])][:4],
                    "kind": str(r.get("kind") or "object"),
                    "is_cheat": bool(r.get("is_cheat")),
                }
            )
        except Exception:
            continue
    return cleaned


def record_tick(
    session_id: int,
    vai_tro: str,
    tick_index: int,
    captured_at: datetime,
    results: list[dict],
    has_alert: bool,
    snapshot_id: int | None,
    event_ids: list[int] | None,
    recv_ts: float,
) -> int | None:
    """Ghi một tick quan sát. Tự tra Candidate từ phiên con; bỏ qua nếu không có."""
    db = SessionLocal()
    try:
        session = (
            db.query(MonitoringSession)
            .options(joinedload(MonitoringSession.candidate))
            .filter(MonitoringSession.PK_MaPhienGiamSat == session_id)
            .first()
        )
        candidate = session.candidate if session is not None else None
        if candidate is None:
            return None

        entry = CandidateTimeline(
            FK_MaPhienGiamSat=session_id,
            FK_MaThiSinh=candidate.PK_MaThiSinh,
            ThoiDiem=captured_at,
            TickIndex=int(tick_index),
            CoCanhBao=bool(has_alert),
            DanhSachPhatHien=_clean_detections(results),
            FK_MaSnapshot=snapshot_id,
            FK_MaSuKien=(event_ids[0] if event_ids else None),
            VaiTroCamera=vai_tro,
            NguonAnh="thumbnail",
        )
        db.add(entry)
        db.flush()
        entry.DoTreMs = max(0, int((time.time() - recv_ts) * 1000))
        db.commit()
        return entry.PK_MaDong
    except Exception as exc:
        db.rollback()
        logger.debug(f"record_tick failed (session={session_id}, role={vai_tro}): {exc}")
        return None
    finally:
        db.close()


def _image_b64(path_str: str | None, max_bytes: int = 900_000) -> str | None:
    """Đọc thumbnail và mã hoá base64 để Streamlit render trực tiếp, không cần auth."""
    if not path_str:
        return None
    try:
        path = Path(path_str)
        if not path.is_file():
            return None
        raw = path.read_bytes()
        if len(raw) > max_bytes:
            return None
        return base64.b64encode(raw).decode("ascii")
    except Exception:
        return None


def _parent_session_join(query, user_id: Optional[int]):
    """Join Candidate → ca thi cha để lọc quyền và lấy phòng/môn."""
    parent = aliased(MonitoringSession)
    query = query.join(Candidate, Candidate.PK_MaThiSinh == CandidateTimeline.FK_MaThiSinh)
    query = query.join(parent, parent.PK_MaPhienGiamSat == Candidate.FK_MaPhienGiamSat)
    if user_id is not None:
        query = query.filter(parent.FK_MaNguoiDung == user_id)
    return query, parent


def list_timeline(
    db: DBSession,
    session_id: Optional[int] = None,
    candidate_id: Optional[int] = None,
    only_alerts: bool = True,
    from_dt: Optional[datetime] = None,
    to_dt: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 30,
    user_id: Optional[int] = None,
    include_image: bool = True,
) -> dict:
    """Trang timeline của tất cả thí sinh, mới nhất trước."""
    query = db.query(CandidateTimeline).options(
        joinedload(CandidateTimeline.candidate),
        joinedload(CandidateTimeline.snapshot),
        joinedload(CandidateTimeline.event),
    )
    query, parent = _parent_session_join(query, user_id)

    if session_id is not None:
        query = query.filter(Candidate.FK_MaPhienGiamSat == session_id)
    if candidate_id is not None:
        query = query.filter(CandidateTimeline.FK_MaThiSinh == candidate_id)
    if only_alerts:
        query = query.filter(CandidateTimeline.CoCanhBao.is_(True))
    if from_dt is not None:
        query = query.filter(CandidateTimeline.ThoiDiem >= from_dt)
    if to_dt is not None:
        query = query.filter(CandidateTimeline.ThoiDiem <= to_dt)

    total = query.count()
    rows = (
        query.order_by(CandidateTimeline.ThoiDiem.desc(), CandidateTimeline.PK_MaDong.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    items = []
    for row in rows:
        event = row.event
        labels = [
            str(d.get("label") or "")
            for d in (row.DanhSachPhatHien or [])
            if d.get("is_cheat")
        ]
        confidences = [
            float(d.get("confidence") or 0.0)
            for d in (row.DanhSachPhatHien or [])
            if d.get("is_cheat")
        ]
        image_path = row.snapshot.DuongDanGoc if row.snapshot is not None else None
        parent_session = row.candidate.exam_session if row.candidate is not None else None
        items.append(
            {
                "PK_MaDong": row.PK_MaDong,
                "thoi_gian": row.ThoiDiem,
                "co_canh_bao": bool(row.CoCanhBao),
                "camera": row.VaiTroCamera or "front",
                "phat_hien": row.DanhSachPhatHien or [],
                "hanh_vi": event.LoaiHanhVi if event is not None else (labels[0] if labels else ""),
                "do_tin_cay": round(max(confidences), 4) if confidences else None,
                "trang_thai": event.TrangThaiKiemTra if event is not None else ("theo_doi" if row.CoCanhBao else None),
                "event_id": event.PK_MaSuKien if event is not None else None,
                "do_tre_ms": row.DoTreMs,
                "image_url": f"/stats/timeline/{row.PK_MaDong}/file",
                "image_b64": _image_b64(image_path) if include_image else None,
                "candidate": (
                    {
                        "PK_MaThiSinh": row.candidate.PK_MaThiSinh,
                        "SBD": row.candidate.SBD,
                        "HoTen": row.candidate.HoTen,
                        "Lop": row.candidate.Lop,
                    }
                    if row.candidate is not None
                    else None
                ),
                "session": {
                    "PK_MaPhienGiamSat": row.FK_MaPhienGiamSat,
                    "parent_session_id": (
                        row.candidate.FK_MaPhienGiamSat if row.candidate is not None else None
                    ),
                    "PhongThi": parent_session.PhongThi if parent_session is not None else None,
                    "MonThi": parent_session.MonThi if parent_session is not None else None,
                },
            }
        )

    return {"total": total, "skip": skip, "limit": limit, "items": items}


def get_timeline_image_path(db: DBSession, entry_id: int, user_id: Optional[int] = None) -> Optional[str]:
    """Đường dẫn thumbnail của một tick, có kiểm tra phạm vi người dùng."""
    query = db.query(CandidateTimeline).options(joinedload(CandidateTimeline.snapshot))
    query = query.filter(CandidateTimeline.PK_MaDong == entry_id)
    if user_id is not None:
        query = query.join(Candidate, Candidate.PK_MaThiSinh == CandidateTimeline.FK_MaThiSinh)
        parent = aliased(MonitoringSession)
        query = query.join(parent, parent.PK_MaPhienGiamSat == Candidate.FK_MaPhienGiamSat)
        query = query.filter(parent.FK_MaNguoiDung == user_id)
    row = query.first()
    if row is None or row.snapshot is None:
        return None
    path = Path(row.snapshot.DuongDanGoc)
    return str(path) if path.is_file() else None


def get_candidate_stats(
    db: DBSession,
    session_id: Optional[int],
    user_id: Optional[int] = None,
    from_dt: Optional[datetime] = None,
    to_dt: Optional[datetime] = None,
) -> list[dict]:
    """Tổng hợp theo từng thí sinh: sự kiện, chờ kiểm tra, tick cảnh báo."""
    parent = aliased(MonitoringSession)
    q_candidates = db.query(Candidate).join(
        parent, parent.PK_MaPhienGiamSat == Candidate.FK_MaPhienGiamSat
    )
    if session_id is not None:
        q_candidates = q_candidates.filter(Candidate.FK_MaPhienGiamSat == session_id)
    if user_id is not None:
        q_candidates = q_candidates.filter(parent.FK_MaNguoiDung == user_id)

    candidates = q_candidates.order_by(Candidate.SBD).all()
    result: list[dict] = []

    for c in candidates:
        sub = (
            db.query(MonitoringSession)
            .filter(MonitoringSession.FK_MaThiSinh == c.PK_MaThiSinh)
            .order_by(MonitoringSession.ThoiGianBatDau.desc())
            .first()
        )
        total_events = 0
        pending_events = 0
        timeline_alerts = 0
        last_alert_at = None
        last_event_id = None
        last_evidence_id = None

        if sub is not None:
            q_events = db.query(DetectedEvent).filter(
                DetectedEvent.FK_MaPhienGiamSat == sub.PK_MaPhienGiamSat
            )
            if from_dt is not None:
                q_events = q_events.filter(DetectedEvent.ThoiGianPhatHien >= from_dt)
            if to_dt is not None:
                q_events = q_events.filter(DetectedEvent.ThoiGianPhatHien <= to_dt)
            total_events = q_events.count()
            pending_events = q_events.filter(
                DetectedEvent.TrangThaiKiemTra == "cho_kiem_tra"
            ).count()
            last_event = q_events.order_by(DetectedEvent.ThoiGianPhatHien.desc()).first()
            if last_event is not None:
                last_alert_at = last_event.ThoiGianPhatHien
                last_event_id = last_event.PK_MaSuKien
                evidence = (
                    db.query(Evidence)
                    .filter(Evidence.FK_MaSuKien == last_event.PK_MaSuKien)
                    .order_by(Evidence.PK_MaBangChung.desc())
                    .first()
                )
                last_evidence_id = evidence.PK_MaBangChung if evidence is not None else None

            q_timeline = db.query(func.count(CandidateTimeline.PK_MaDong)).filter(
                CandidateTimeline.FK_MaPhienGiamSat == sub.PK_MaPhienGiamSat,
                CandidateTimeline.CoCanhBao.is_(True),
            )
            if from_dt is not None:
                q_timeline = q_timeline.filter(CandidateTimeline.ThoiDiem >= from_dt)
            if to_dt is not None:
                q_timeline = q_timeline.filter(CandidateTimeline.ThoiDiem <= to_dt)
            timeline_alerts = q_timeline.scalar() or 0

        result.append(
            {
                "candidate": {
                    "PK_MaThiSinh": c.PK_MaThiSinh,
                    "SBD": c.SBD,
                    "HoTen": c.HoTen,
                    "Lop": c.Lop,
                },
                "session_id": sub.PK_MaPhienGiamSat if sub is not None else None,
                "total_events": total_events,
                "pending_events": pending_events,
                "timeline_alerts": timeline_alerts,
                "last_alert_at": last_alert_at,
                "last_event_id": last_event_id,
                "last_evidence_id": last_evidence_id,
            }
        )

    return result


def get_overview(
    db: DBSession,
    session_id: Optional[int],
    user_id: Optional[int] = None,
    from_dt: Optional[datetime] = None,
    to_dt: Optional[datetime] = None,
) -> dict:
    """KPI tổng hợp đúng nghĩa thí sinh + cảnh báo + độ trễ tick."""
    parent = aliased(MonitoringSession)
    q_candidates = db.query(func.count(Candidate.PK_MaThiSinh)).join(
        parent, parent.PK_MaPhienGiamSat == Candidate.FK_MaPhienGiamSat
    )
    if session_id is not None:
        q_candidates = q_candidates.filter(Candidate.FK_MaPhienGiamSat == session_id)
    if user_id is not None:
        q_candidates = q_candidates.filter(parent.FK_MaNguoiDung == user_id)
    total_students = q_candidates.scalar() or 0

    timeline_query = db.query(CandidateTimeline).join(
        Candidate, Candidate.PK_MaThiSinh == CandidateTimeline.FK_MaThiSinh
    ).join(parent, parent.PK_MaPhienGiamSat == Candidate.FK_MaPhienGiamSat)
    if session_id is not None:
        timeline_query = timeline_query.filter(Candidate.FK_MaPhienGiamSat == session_id)
    if user_id is not None:
        timeline_query = timeline_query.filter(parent.FK_MaNguoiDung == user_id)
    if from_dt is not None:
        timeline_query = timeline_query.filter(CandidateTimeline.ThoiDiem >= from_dt)
    if to_dt is not None:
        timeline_query = timeline_query.filter(CandidateTimeline.ThoiDiem <= to_dt)

    students_with_alerts = (
        timeline_query.filter(CandidateTimeline.CoCanhBao.is_(True))
        .with_entities(func.count(func.distinct(CandidateTimeline.FK_MaThiSinh)))
        .scalar()
        or 0
    )
    total_timeline_alerts = timeline_query.filter(
        CandidateTimeline.CoCanhBao.is_(True)
    ).count()

    latency_rows = (
        timeline_query.filter(CandidateTimeline.DoTreMs.isnot(None))
        .with_entities(CandidateTimeline.DoTreMs)
        .all()
    )
    latencies = [int(r[0]) for r in latency_rows if r[0] is not None]
    avg_latency = round(sum(latencies) / len(latencies), 1) if latencies else None
    max_latency = max(latencies) if latencies else None

    # Sự kiện nghiệp vụ (đã debounce) để so sánh với timeline.
    q_events = db.query(func.count(DetectedEvent.PK_MaSuKien)).join(
        MonitoringSession,
        MonitoringSession.PK_MaPhienGiamSat == DetectedEvent.FK_MaPhienGiamSat,
    )
    if session_id is not None:
        q_events = q_events.join(
            Candidate, Candidate.PK_MaThiSinh == MonitoringSession.FK_MaThiSinh
        ).filter(Candidate.FK_MaPhienGiamSat == session_id)
    if user_id is not None:
        q_events = q_events.join(
            parent, parent.PK_MaPhienGiamSat == MonitoringSession.PK_MaPhienGiamSat
        ).filter(parent.FK_MaNguoiDung == user_id)
    if from_dt is not None:
        q_events = q_events.filter(DetectedEvent.ThoiGianPhatHien >= from_dt)
    if to_dt is not None:
        q_events = q_events.filter(DetectedEvent.ThoiGianPhatHien <= to_dt)
    total_events = q_events.scalar() or 0

    q_pending = db.query(func.count(DetectedEvent.PK_MaSuKien)).join(
        MonitoringSession,
        MonitoringSession.PK_MaPhienGiamSat == DetectedEvent.FK_MaPhienGiamSat,
    ).filter(DetectedEvent.TrangThaiKiemTra == "cho_kiem_tra")
    if session_id is not None:
        q_pending = q_pending.join(
            Candidate, Candidate.PK_MaThiSinh == MonitoringSession.FK_MaThiSinh
        ).filter(Candidate.FK_MaPhienGiamSat == session_id)
    if user_id is not None:
        q_pending = q_pending.join(
            parent, parent.PK_MaPhienGiamSat == MonitoringSession.PK_MaPhienGiamSat
        ).filter(parent.FK_MaNguoiDung == user_id)
    if from_dt is not None:
        q_pending = q_pending.filter(DetectedEvent.ThoiGianPhatHien >= from_dt)
    if to_dt is not None:
        q_pending = q_pending.filter(DetectedEvent.ThoiGianPhatHien <= to_dt)
    pending_events = q_pending.scalar() or 0

    clean_rate = (
        round(1.0 - (students_with_alerts / total_students), 4) if total_students else 1.0
    )

    return {
        "total_students": total_students,
        "students_with_alerts": students_with_alerts,
        "total_timeline_alerts": total_timeline_alerts,
        "total_events": total_events,
        "pending_events": pending_events,
        "clean_rate": clean_rate,
        "avg_latency_ms": avg_latency,
        "max_latency_ms": max_latency,
    }
