"""Endpoint thí sinh: nhập danh sách, vào thi bằng SBD, lưới giám thị.
Logic chính: giám thị cần đăng nhập; thí sinh join chỉ cần SBD đúng ca đang mở.
"""

import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.dependencies import get_current_user
from core.logger import get_logger
from crud.candidate_crud import (
    count_unverified_by_candidate,
    create_sub_session,
    find_candidate_for_join,
    get_camera_streams,
    get_latest_evidence_image,
    get_latest_sub_session,
    get_open_sub_session,
    import_candidates,
    latest_evidence_time,
    list_candidates,
)
from crud.session_crud import end_session, get_session_by_id
from database.database import get_db
from models.detected_event import DetectedEvent
from models.monitoring_session import MonitoringSession
from models.user import User
from pydantic import BaseModel, Field

from schemas.candidate import (
    CameraStreamResponse,
    CandidateImport,
    CandidateJoin,
    CandidateJoinResponse,
    CandidateResponse,
    StreamTokenResponse,
)
from schemas.ingest import CandidateStatusItem
from service import ingest_service

logger = get_logger(__name__)
router = APIRouter(prefix="/candidates", tags=["ThiSinh"])


class CandidateFinish(BaseModel):
    session_id: int
    token: str


class CreateOnlineSession(BaseModel):
    PhongThi: str = Field(..., min_length=1, max_length=50)
    MonThi: str = Field(..., min_length=1, max_length=255)


def _utc_timestamp(value: datetime | None) -> float:
    """Đổi datetime lưu trong DB sang epoch giây.

    PostgreSQL TIMESTAMP (không kèm múi giờ) trả về datetime naive theo UTC,
    nên phải gắn tzinfo=UTC trước khi .timestamp() để không lệch múi giờ máy chủ.
    """
    if value is None:
        return 0.0
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.timestamp()


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
    """Thí sinh vào thi chỉ cần SBD. Idempotent: vào lại trả phiên đang mở + token mới.

    VaiTro=front cho webcam máy tính; VaiTro=side cho điện thoại phụ. Cả hai dùng
    chung phiên con của thí sinh nhưng có token/worker riêng.
    """
    from database.database import SessionLocal

    role = (data.VaiTro or "front").lower()
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

        # 1. BẮT BUỘC kiểm tra ca thi cha TRƯỚC TIÊN (bất kể thí sinh đã từng có sub-session hay chưa)
        exam = get_session_by_id(db, candidate.FK_MaPhienGiamSat)
        if not exam or exam.TrangThai != "dang_giam_sat" or exam.ThoiGianKetThuc is not None:
            # Thu hồi và chốt sạch mọi sub-session còn sót của thí sinh này
            lingering = (
                db.query(MonitoringSession)
                .filter(
                    MonitoringSession.FK_MaThiSinh == candidate.PK_MaThiSinh,
                    MonitoringSession.TrangThai == "dang_giam_sat",
                )
                .all()
            )
            for l_sub in lingering:
                end_session(db, l_sub.PK_MaPhienGiamSat)
                try:
                    ingest_service.stop_session_workers(l_sub.PK_MaPhienGiamSat)
                except Exception:
                    pass
            raise HTTPException(
                status_code=403,
                detail="Ca thi chưa mở hoặc đã kết thúc. Vui lòng liên hệ giám thị để mở ca thi.",
            )

        # 2. Khi ca thi cha đang mở hợp lệ: lấy sub-session hiện có hoặc mở mới
        sub = get_open_sub_session(db, candidate.PK_MaThiSinh)
        if not sub:
            sub = create_sub_session(db, exam.FK_MaNguoiDung, candidate)

        token = ingest_service.mint_token(sub.PK_MaPhienGiamSat, role)
        ingest_service.ensure_worker(sub.PK_MaPhienGiamSat, role)

        # Tự động cấp trước link & token camera phụ cho thí sinh (dùng cho điện thoại góc nghiêng/sau)
        from models.camera_stream import CameraStream

        side_stream = (
            db.query(CameraStream)
            .filter(
                CameraStream.FK_MaPhienGiamSat == sub.PK_MaPhienGiamSat,
                CameraStream.VaiTro == "side",
            )
            .first()
        )
        if side_stream is not None and side_stream.Token and side_stream.TrangThai != "ket_thuc":
            side_token = side_stream.Token
        else:
            side_token = ingest_service.mint_token(sub.PK_MaPhienGiamSat, "side")

        side_exam_url = f"/exam?session_id={sub.PK_MaPhienGiamSat}&role=side&token={side_token}"

        return CandidateJoinResponse(
            PK_MaPhienGiamSat=sub.PK_MaPhienGiamSat,
            VaiTro=role,
            token=token,
            candidate=candidate,
            side_token=side_token,
            side_exam_url=side_exam_url,
        )
    finally:
        db.close()


@router.get("/session/{session_id}/side-status")
def get_side_camera_status(session_id: int):
    """Kiểm tra camera phụ của thí sinh đã kết nối và gửi frame hay chưa (public cho exam.html)."""
    from database.database import SessionLocal
    from models.camera_stream import CameraStream

    db = SessionLocal()
    try:
        sub = get_session_by_id(db, session_id)
        if not sub or sub.TrangThai != "dang_giam_sat":
            return {"connected": False, "active": False}
        stream = (
            db.query(CameraStream)
            .filter(
                CameraStream.FK_MaPhienGiamSat == session_id,
                CameraStream.VaiTro == "side",
            )
            .first()
        )
        is_active = (
            stream is not None
            and stream.TrangThai == "dang_hoat_dong"
            and stream.LanCuoiNhan is not None
            and (time.time() - _utc_timestamp(stream.LanCuoiNhan)) < 15
        )
        return {
            "connected": stream is not None and stream.Token is not None,
            "active": is_active,
            "joined": stream is not None and stream.TrangThai != "ket_thuc",
        }
    finally:
        db.close()


@router.get("/session/{session_id}/status")
def get_exam_session_status(session_id: int):
    """Kiểm tra ca thi online có đang mở hay không (public cho trang exam.html)."""
    from database.database import SessionLocal

    db = SessionLocal()
    try:
        exam = get_session_by_id(db, session_id)
        if not exam:
            return {"session_id": session_id, "exists": False, "is_open": False}
        is_open = (exam.TrangThai == "dang_giam_sat" and exam.ThoiGianKetThuc is None)
        return {
            "session_id": session_id,
            "exists": True,
            "is_open": is_open,
            "TrangThai": exam.TrangThai,
            "PhongThi": exam.PhongThi,
            "MonThi": exam.MonThi,
        }
    finally:
        db.close()


@router.get("/session/{session_id}/attach")
def attach_stream(session_id: int, token: str):
    """Dùng token có sẵn trong link camera (front/side) để lấy lại thông tin phiên.

    Không mint token mới nên link điện thoại gửi thí sinh giữ nguyên hiệu lực
    cho tới khi giám thị kết thúc ca hoặc thu hồi luồng.
    """
    from database.database import SessionLocal

    resolved = ingest_service.resolve_token(token)
    if not resolved or resolved[0] != session_id:
        raise HTTPException(status_code=401, detail="Token camera không hợp lệ hoặc đã hết hiệu lực.")

    db = SessionLocal()
    try:
        sub = get_session_by_id(db, session_id)
        if not sub or sub.TrangThai != "dang_giam_sat" or sub.ThoiGianKetThuc is not None:
            raise HTTPException(status_code=403, detail="Ca thi chưa mở hoặc đã kết thúc.")
        candidate = None
        if sub.FK_MaThiSinh is not None:
            candidate = sub.candidate
            if candidate:
                exam = get_session_by_id(db, candidate.FK_MaPhienGiamSat)
                if not exam or exam.TrangThai != "dang_giam_sat" or exam.ThoiGianKetThuc is not None:
                    end_session(db, session_id)
                    raise HTTPException(status_code=403, detail="Ca thi chưa mở hoặc đã kết thúc.")
        ingest_service.ensure_worker(session_id, resolved[1])
        return {
            "PK_MaPhienGiamSat": session_id,
            "VaiTro": resolved[1],
            "token": token,
            "candidate": CandidateResponse.model_validate(candidate) if candidate else None,
            "PhongThi": sub.PhongThi,
            "MonThi": sub.MonThi,
        }
    finally:
        db.close()


@router.post("/session/{session_id}/stream/{vai_tro}/token", response_model=StreamTokenResponse)
def create_stream_link(
    session_id: int,
    vai_tro: str,
    refresh: bool = False,
    user: User = Depends(get_current_user),
):
    """Giám thị cấp link camera phụ (điện thoại) cho một phiên con đang mở.

    Mặc định tái sử dụng token đang có để link đã gửi thí sinh không bị vô hiệu
    mỗi lần dashboard tự làm mới. refresh=true mới cấp token mới.
    """
    from database.database import SessionLocal
    from models.camera_stream import CameraStream

    if vai_tro not in ingest_service.VALID_ROLES:
        raise HTTPException(status_code=400, detail="Vai trò camera phải là 'front' hoặc 'side'.")

    db = SessionLocal()
    try:
        sub = get_session_by_id(db, session_id)
        if not sub or sub.FK_MaThiSinh is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên con của thí sinh.")
        if sub.TrangThai != "dang_giam_sat":
            raise HTTPException(status_code=400, detail="Phiên thi đã kết thúc.")

        stream = (
            db.query(CameraStream)
            .filter(
                CameraStream.FK_MaPhienGiamSat == session_id,
                CameraStream.VaiTro == vai_tro,
            )
            .first()
        )
        if not refresh and stream is not None and stream.Token and stream.TrangThai != "ket_thuc":
            token = stream.Token
        else:
            token = ingest_service.mint_token(session_id, vai_tro)

        # Không tạo worker ở đây: chỉ khi điện thoại thật sự attach/gửi frame mới
        # mở luồng, tránh dashboard báo "camera phụ đang hoạt động" sai.
        exam_url = f"/exam?session_id={session_id}&role={vai_tro}&token={token}"
        return StreamTokenResponse(
            PK_MaPhienGiamSat=session_id,
            VaiTro=vai_tro,
            token=token,
            exam_url=exam_url,
        )
    finally:
        db.close()


@router.get("/session/{session_id}/streams", response_model=list[CameraStreamResponse])
def list_streams(
    session_id: int,
    user: User = Depends(get_current_user),
):
    """Trạng thái các luồng camera của phiên con (front/side)."""
    from database.database import SessionLocal

    db = SessionLocal()
    try:
        return get_camera_streams(db, session_id)
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
        now = time.time()
        for c in list_candidates(db, session_id):
            open_sub = get_open_sub_session(db, c.PK_MaThiSinh)
            latest_sub = open_sub or get_latest_sub_session(db, c.PK_MaThiSinh)
            sid = latest_sub.PK_MaPhienGiamSat if latest_sub else None
            total, pending = (0, 0)
            latest = None
            is_active = False
            front_active = False
            side_active = False
            side_joined = False

            if open_sub:
                activity = ingest_service.get_stream_activity(open_sub.PK_MaPhienGiamSat)
                front_active = activity.get(ingest_service.ROLE_FRONT, False)
                side_active = activity.get(ingest_service.ROLE_SIDE, False)
                is_active = front_active or side_active
                streams = get_camera_streams(db, open_sub.PK_MaPhienGiamSat)
                side_joined = any(
                    s.VaiTro == ingest_service.ROLE_SIDE
                    and s.Token
                    and s.TrangThai != "ket_thuc"
                    for s in streams
                )
                # Thí sinh vừa join, worker chưa kịp nhận frame đầu tiên.
                if not is_active and (now - _utc_timestamp(open_sub.ThoiGianBatDau) <= 30.0):
                    is_active = front_active = True

            last_behavior = None
            last_event_time = None
            if sid:
                total, pending = count_unverified_by_candidate(db, sid)
                latest = latest_evidence_time(db, sid)
                last_event = (
                    db.query(DetectedEvent)
                    .filter(DetectedEvent.FK_MaPhienGiamSat == sid)
                    .order_by(DetectedEvent.ThoiGianPhatHien.desc())
                    .first()
                )
                if last_event:
                    last_behavior = last_event.NhanNguoiDung or last_event.LoaiHanhVi
                    last_event_time = last_event.ThoiGianPhatHien

            items.append(
                CandidateStatusItem(
                    PK_MaThiSinh=c.PK_MaThiSinh,
                    SBD=c.SBD,
                    HoTen=c.HoTen,
                    Lop=c.Lop,
                    PK_MaPhienGiamSat=sid,
                    dang_giam_sat=is_active,
                    camera_front_active=front_active,
                    camera_side_active=side_active,
                    camera_side_joined=side_joined,
                    cho_kiem_tra=pending,
                    tong_su_kien=total,
                    anh_moi_nhat=latest,
                    hanh_vi_moi_nhat=last_behavior,
                    thoi_gian_vi_pham=last_event_time,
                )
            )
        return items
    finally:
        db.close()


@router.post("/finish")
def finish_exam(data: CandidateFinish):
    """Thí sinh tự kết thúc bài thi từ trình duyệt. Xác thực qua token, không cần JWT giám thị."""
    from database.database import SessionLocal

    resolved = ingest_service.resolve_token(data.token)
    if not resolved or resolved[0] != data.session_id:
        raise HTTPException(
            status_code=400,
            detail="Token kết thúc bài thi không hợp lệ hoặc ca thi đã kết thúc.",
        )
    if resolved[1] != ingest_service.ROLE_FRONT:
        # Camera phụ (điện thoại) không được kết thúc bài thi của thí sinh.
        raise HTTPException(
            status_code=403,
            detail="Chỉ camera trước (máy tính) mới được kết thúc bài thi.",
        )
    db = SessionLocal()
    try:
        sub = get_session_by_id(db, data.session_id)
        if not sub or sub.FK_MaThiSinh is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên con của thí sinh.")
        end_session(db, data.session_id)
        ingest_service.stop_session_workers(data.session_id)
        return {"message": "Đã kết thúc bài thi thành công", "session_id": data.session_id}
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
@router.post("/sessions/{session_id}/open")
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
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.error(f"open_exam_session error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi mở ca thi: {str(exc)}")
    finally:
        db.close()


@router.post("/session/{session_id}/close")
@router.post("/sessions/{session_id}/close")
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
        try:
            candidates = list_candidates(db, session_id)
            cand_ids = [c.PK_MaThiSinh for c in candidates]
            if cand_ids:
                open_subs = (
                    db.query(MonitoringSession)
                    .filter(
                        MonitoringSession.FK_MaThiSinh.in_(cand_ids),
                        MonitoringSession.TrangThai == "dang_giam_sat",
                    )
                    .all()
                )
                for sub in open_subs:
                    end_session(db, sub.PK_MaPhienGiamSat)
                    try:
                        ingest_service.stop_session_workers(sub.PK_MaPhienGiamSat)
                    except Exception as wex:
                        logger.warning(f"Lỗi dừng worker cho sub session {sub.PK_MaPhienGiamSat}: {wex}")
        except Exception as cex:
            logger.warning(f"Lỗi duyệt thí sinh khi kết thúc ca thi: {cex}")

        return {
            "message": "Ca thi đã kết thúc",
            "session_id": session_id,
            "TrangThai": "ket_thuc",
        }
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.error(f"close_exam_session error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi kết thúc ca thi: {str(exc)}")
    finally:
        db.close()


@router.post("/session")
@router.post("/sessions")
@router.post("/session/create")
@router.post("/sessions/create")
@router.post("/create-session")
def create_online_session(
    data: CreateOnlineSession,
    user: User = Depends(get_current_user),
):
    """Tạo mới ca thi online ở trạng thái đang mở."""
    from datetime import datetime, timezone
    from database.database import SessionLocal
    from models.monitoring_session import MonitoringSession
    from models.edgedevice import EdgeDevice
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy import text

    db = SessionLocal()
    try:
        # Thử DROP NOT NULL nếu cột FK_MaThietBi vẫn còn constraint NOT NULL cũ
        try:
            db.execute(text('ALTER TABLE tbl_monitoring_sessions ALTER COLUMN "FK_MaThietBi" DROP NOT NULL;'))
            db.commit()
        except Exception:
            db.rollback()

        session = MonitoringSession(
            ThoiGianBatDau=datetime.now(timezone.utc),
            PhongThi=data.PhongThi.strip(),
            MonThi=data.MonThi.strip(),
            FK_MaNguoiDung=user.PK_MaNguoiDung,
            FK_MaThietBi=None,
            TrangThai="dang_giam_sat",
        )
        db.add(session)
        try:
            db.commit()
        except IntegrityError:
            # Fallback nếu DB vẫn ép FK_MaThietBi NOT NULL và không cho phép ALTER
            db.rollback()
            first_dev = db.query(EdgeDevice).first()
            session.FK_MaThietBi = first_dev.PK_MaThietBi if first_dev else None
            db.add(session)
            db.commit()

        db.refresh(session)
        return {
            "PK_MaPhienGiamSat": session.PK_MaPhienGiamSat,
            "PhongThi": session.PhongThi,
            "MonThi": session.MonThi,
            "TrangThai": session.TrangThai,
        }
    except Exception as exc:
        db.rollback()
        logger.error(f"create_online_session error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi tạo ca thi: {str(exc)}")
    finally:
        db.close()


@router.get("/session/{session_id}/snapshot")
def get_candidate_snapshot_endpoint(
    session_id: int,
    role: str | None = None,
    variant: str = "auto",
    user: User = Depends(get_current_user),
):
    """Trả ảnh snapshot mới nhất của thí sinh.

    role: front/side (rỗng = ưu tiên camera trước rồi camera phụ).
    variant: auto (live frame -> ảnh dẫn xuất -> bằng chứng), normalized,
             thumbnail hoặc annotated.
    """
    from pathlib import Path
    from fastapi import Response
    from fastapi.responses import FileResponse
    from database.database import SessionLocal
    from service import snapshot_service

    role = role if role in ingest_service.VALID_ROLES else None
    variant = variant if variant in {"normalized", "thumbnail", "annotated"} else "auto"

    # 1. Live frame đã vẽ overlay AI (nếu worker còn chạy)
    if variant == "auto":
        live_jpg = ingest_service.get_latest_frame(session_id, role)
        if live_jpg:
            return Response(content=live_jpg, media_type="image/jpeg")

    # 2. Ảnh dẫn xuất từ pipeline snapshot (raw -> normalized/thumbnail/annotated)
    db = SessionLocal()
    try:
        loai_anh = "thumbnail" if variant == "auto" else variant
        img_path = snapshot_service.latest_snapshot_path(
            db, session_id, vai_tro=role, loai_anh=loai_anh
        )
        if img_path:
            p = Path(img_path)
            if p.is_file():
                return FileResponse(p, media_type="image/jpeg")

        # 3. Tương thích ngược: ảnh bằng chứng sự kiện cũ
        img_path = get_latest_evidence_image(db, session_id, vai_tro=role)
        if img_path:
            p = Path(img_path)
            if p.is_file():
                return FileResponse(p, media_type="image/jpeg")
    finally:
        db.close()

    raise HTTPException(status_code=404, detail="Chưa có ảnh snapshot")


