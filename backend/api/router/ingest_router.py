"""Endpoint ingest frame thi online từ trình duyệt thí sinh.
Logic chính: xác thực token nộp bài (không cần JWT giám thị); validate kỹ
rồi xếp hàng 202 ngay, infer chạy nền trong worker theo phiên.
"""

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from core.logger import get_logger
from schemas.ingest import IngestAccepted
from service import ingest_service

logger = get_logger(__name__)
router = APIRouter(prefix="/ingest", tags=["Ingest"])


@router.post("/frame", response_model=IngestAccepted, status_code=202)
async def ingest_frame(
    session_id: int = Form(...),
    token: str = Form(...),
    ts_client: float = Form(...),
    frame: UploadFile = File(...),
):
    """Nhận 1 frame JPEG từ browser. Trả 202 ngay khi xếp hàng thành công."""
    try:
        jpg = await frame.read()
    except Exception as exc:
        logger.warning(f"Ingest read failed: {exc}")
        raise HTTPException(status_code=400, detail="không đọc được file ảnh")

    ok, reason = ingest_service.ingest_frame(session_id, token, ts_client, jpg)
    if not ok:
        raise HTTPException(status_code=400, detail=reason)
    return IngestAccepted(PK_MaPhienGiamSat=session_id, queued=True)
