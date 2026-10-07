"""Endpoint thí sinh: nhập danh sách, vào thi bằng SBD, lưới giám thị.
Logic chính: giám thị cần đăng nhập; thí sinh join chỉ cần SBD đúng ca đang mở.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.dependencies import get_current_user
from core.logger import get_logger
from crud.candidate_crud import (
    count_unverified_by_candidate,
    create_sub_session,
    find_candidate_for_join,
    get_open_sub_session,
    import_candidates,
    latest_evidence_time,
    list_candidates,
)
from crud.session_crud import end_session, get_session_by_id
from database.database import get_db
from models.user import User
from pydantic import BaseModel, Field

from schemas.candidate import (
    CandidateImport,
    CandidateJoin,
    CandidateJoinResponse,
    CandidateResponse,
)
from schemas.ingest import CandidateStatusItem
from service import ingest_service

logger = get_logger(__name__)
router = APIRouter(prefix="/candidates", tags=["ThiSinh"])


class CreateOnlineSession(BaseModel):
    PhongThi: str = Field(..., min_length=1, max_length=50)
    MonThi: str = Field(..., min_length=1, max_length=255)


@router.post("/import", response_model=list[CandidateResponse])
def import_list(
    data: CandidateImport,
    user: User = Depends(get_current_user),
):
    """Giám thị nhập danh sách thí sinh (SBD, họ tên, lớp) cho ca thi."""
    from database.database import SessionLocal

    db = SessionLocal()
    try:
        exam = get_session_by_id(db, data.FK_MaPhienGiamSat)
        if not exam:
            raise HTTPException(status_code=404, detail="Không tìm thấy ca thi")
        saved, duplicates = import_candidates(
            db,
            data.FK_MaPhienGiamSat,
            [c.model_dump() for c in data.candidates],
        )
        if duplicates:
            logger.warning(f"SBD trùng trong file nhập: {duplicates}")
        return saved
    finally:
        db.close()


@router.get("", response_model=list[CandidateResponse])
def list_all(
    session_id: int,
    user: User = Depends(get_current_user),
):
    """Liệt kê thí sinh của ca thi."""
    from database.database import SessionLocal

    db = SessionLocal()
    try:
        return list_candidates(db, session_id)
    finally:
        db.close()


@router.post("/join", response_model=CandidateJoinResponse)
def join_exam(data: CandidateJoin):
    """Thí sinh vào thi chỉ cần SBD. Idempotent: vào lại trả phiên đang mở + token mới."""
    from database.database import SessionLocal

    db = SessionLocal()
    try:
        candidate = find_candidate_for_join(
            db, data.SBD, data.FK_MaPhienGiamSat
        )
        if not candidate:
            raise HTTPException(
                status_code=404,
                detail=f"Không tìm thấy SBD '{data.SBD}' trong danh sách ca thi",
            )
        sub = get_open_sub_session(db, candidate.PK_MaThiSinh)
        if not sub:
            exam = get_session_by_id(db, candidate.FK_MaPhienGiamSat)
            if not exam or exam.TrangThai != "dang_giam_sat":
                raise HTTPException(
                    status_code=403,
                    detail="Ca thi chưa mở hoặc đã kết thúc. Vui lòng liên hệ giám thị để mở ca thi.",
                )
            sub = create_sub_session(db, exam.FK_MaNguoiDung, candidate)
        token = ingest_service.mint_token(sub.PK_MaPhienGiamSat)
        ingest_service.ensure_worker(sub.PK_MaPhienGiamSat)
        return CandidateJoinResponse(
            PK_MaPhienGiamSat=sub.PK_MaPhienGiamSat,
            token=token,
            candidate=candidate,
        )
    finally:
        db.close()


@router.get("/overview", response_model=list[CandidateStatusItem])
def exam_overview(
    session_id: int,
    user: User = Depends(get_current_user),
):
    """Lưới giám thị: trạng thái từng thí sinh trong ca (phiên con, chờ kiểm tra, ảnh mới nhất)."""
    from database.database import SessionLocal

    db = SessionLocal()
    try:
        items: list[CandidateStatusItem] = []
        for c in list_candidates(db, session_id):
            sub = get_open_sub_session(db, c.PK_MaThiSinh)
            sid = sub.PK_MaPhienGiamSat if sub else None
            total, pending = (0, 0)
            latest = None
            if sid:
                total, pending = count_unverified_by_candidate(db, sid)
                latest = latest_evidence_time(db, sid)
            items.append(
                CandidateStatusItem(
                    PK_MaThiSinh=c.PK_MaThiSinh,
                    SBD=c.SBD,
                    HoTen=c.HoTen,
                    Lop=c.Lop,
                    PK_MaPhienGiamSat=sid,
                    dang_giam_sat=sid is not None,
                    cho_kiem_tra=pending,
                    tong_su_kien=total,
                    anh_moi_nhat=latest,
                )
            )
        return items
    finally:
        db.close()


@router.post("/leave/{session_id}")
def leave_exam(
    session_id: int,
    user: User = Depends(get_current_user),
):
    """Chốt phiên con (thí sinh nộp bài / giám thị đóng). Dừng worker + thu hồi token."""
    from database.database import SessionLocal

    db = SessionLocal()
    try:
        sub = get_session_by_id(db, session_id)
        if not sub or sub.FK_MaThiSinh is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên con")
        end_session(db, session_id)
        ingest_service.stop_session_workers(session_id)
        return {"message": "Đã chốt phiên", "session_id": session_id}
    finally:
        db.close()


@router.post("/session/{session_id}/open")
def open_exam_session(
    session_id: int,
    user: User = Depends(get_current_user),
):
    """Giám thị mở ca thi để thí sinh có thể vào phòng thi."""
    from database.database import SessionLocal

    db = SessionLocal()
    try:
        exam = get_session_by_id(db, session_id)
        if not exam:
            raise HTTPException(status_code=404, detail="Không tìm thấy ca thi")
        exam.TrangThai = "dang_giam_sat"
        exam.ThoiGianKetThuc = None
        db.commit()
        return {
            "message": "Ca thi đã được mở",
            "session_id": session_id,
            "TrangThai": "dang_giam_sat",
        }
    finally:
        db.close()


@router.post("/session/{session_id}/close")
def close_exam_session(
    session_id: int,
    user: User = Depends(get_current_user),
):
    """Giám thị kết thúc ca thi và chốt phiên tất cả thí sinh."""
    from database.database import SessionLocal

    db = SessionLocal()
    try:
        exam = get_session_by_id(db, session_id)
        if not exam:
            raise HTTPException(status_code=404, detail="Không tìm thấy ca thi")
        end_session(db, session_id)
        for c in list_candidates(db, session_id):
            sub = get_open_sub_session(db, c.PK_MaThiSinh)
            if sub:
                end_session(db, sub.PK_MaPhienGiamSat)
                ingest_service.stop_session_workers(sub.PK_MaPhienGiamSat)
        return {
            "message": "Ca thi đã kết thúc",
            "session_id": session_id,
            "TrangThai": "ket_thuc",
        }
    finally:
        db.close()


@router.post("/session/create")
def create_online_session(
    data: CreateOnlineSession,
    user: User = Depends(get_current_user),
):
    """Tạo mới ca thi online ở trạng thái đang mở."""
    from datetime import datetime, timezone
    from database.database import SessionLocal
    from models.monitoring_session import MonitoringSession

    db = SessionLocal()
    try:
        session = MonitoringSession(
            ThoiGianBatDau=datetime.now(timezone.utc),
            PhongThi=data.PhongThi.strip(),
            MonThi=data.MonThi.strip(),
            FK_MaNguoiDung=user.PK_MaNguoiDung,
            FK_MaThietBi=None,
            TrangThai="dang_giam_sat",
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return {
            "PK_MaPhienGiamSat": session.PK_MaPhienGiamSat,
            "PhongThi": session.PhongThi,
            "MonThi": session.MonThi,
            "TrangThai": session.TrangThai,
        }
    finally:
        db.close()

