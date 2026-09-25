"""Quản lý frame: dữ liệu phân tích, chi tiết, sửa nhãn.
Luồng chính: đọc frame → đếm gian lận theo nhãn cuối → sửa nhãn thì tính lại thống kê."""

import ast

from sqlalchemy.orm import Session as DBSession

from core.exceptions import NotFoundError
from core.logger import get_logger
from ai_model.ai_pipeline import is_cheat_label
from crud.ai_result_crud import get_ai_results_by_frame, get_ai_results_by_frames, update_ai_result_label
from crud.frame_crud import get_frame_by_id, get_frames_by_session
from crud.statistics_crud import recalculate_statistics_for_frame
from utils.label_utils import get_final_label

logger = get_logger(__name__)


def get_analysis_data(
    db: DBSession, session_id: int, skip: int = 0, limit: int = 50
) -> list[dict]:
    """Tính số lượng sạch/gian lận từng frame trong ca.
    Điểm logic: nhãn gian lận là Cheat_Paper và cellphone; cheat-rate suy ra từ hai số đếm."""
    frames = get_frames_by_session(db, session_id, skip=skip, limit=limit)

    # Lấy gộp toàn bộ kết quả AI một lần để tránh truy vấn lặp theo từng frame
    frame_ids = [frame.frame_id for frame in frames]
    all_ai_results = get_ai_results_by_frames(db, frame_ids)

    # Gom kết quả theo frame_id
    results_by_frame = {frame_id: [] for frame_id in frame_ids}
    for r in all_ai_results:
        results_by_frame[r.frame_id].append(r)

    data: list[dict] = []
    for frame in frames:
        results = results_by_frame.get(frame.frame_id, [])

        sleeping = sum(
            1 for r in results if is_cheat_label(get_final_label(r) or "")
        )
        total = len(results)

        data.append({
            "frame_id": frame.frame_id,
            "image_path": frame.image_path,
            "extracted_at": frame.extracted_at,
            "focus_count": total - sleeping,
            "sleeping_count": sleeping,
            "total_students": total,
        })

    return data


def get_frame_detail(db: DBSession, frame_id: int) -> dict:
    """
    Trả chi tiết một frame gồm toàn bộ detection.
    Điểm logic: đếm gian lận theo nhãn cuối (ưu tiên nhãn người dùng sửa);
    bbox chữ được phân tích an toàn, hỏng thì bỏ qua.

    Raises:
        NotFoundError: Frame không tồn tại.
    """
    frame = get_frame_by_id(db, frame_id)
    if not frame:
        raise NotFoundError(detail="Frame not found")

    rows = get_ai_results_by_frame(db, frame_id)
    total = len(rows)
    # Dùng nhãn cuối để tôn trọng phần người dùng đã sửa
    sleeping = sum(1 for r in rows if is_cheat_label(get_final_label(r) or ""))
    avg_conf = round(sum(r.confidence for r in rows) / total, 2) if total else 0.0

    detections = []
    for i, r in enumerate(rows, start=1):
        bbox = None
        if r.face_bbox:
            try:
                bbox = ast.literal_eval(r.face_bbox)
            except (ValueError, SyntaxError):
                bbox = None

        detections.append({
            "result_id": r.result_id,
            "student_id": f"HS{i}",
            "status": get_final_label(r),
            "confidence": r.confidence,
            "user_label": r.user_label,
            "face_bbox": bbox,
        })

    return {
        "frame_id": frame.frame_id,
        "session_id": frame.session_id,
        "image_path": frame.image_path,
        "total_students": total,
        "sleeping_count": sleeping,
        "focus_count": total - sleeping,
        "avg_confidence": avg_conf,
        "detections": detections,
    }


def update_result_label(db: DBSession, result_id: int, status: str) -> dict:
    """
    Ghi nhận nhãn do người dùng sửa rồi tính lại thống kê của ca chứa frame.
    Điểm logic: sửa nhãn xong phải recalculate để dashboard và chi tiết ca đổi theo.

    Raises:
        NotFoundError: Kết quả AI không tồn tại.
    """
    record = update_ai_result_label(db, result_id, status)
    if not record:
        raise NotFoundError(detail="AI result not found")

    # Tính lại thống kê của ca sở hữu frame này
    frame = get_frame_by_id(db, record.frame_id)
    if frame and frame.session_id:
        recalculate_statistics_for_frame(db, frame.session_id, record.frame_id)
        logger.info(
            f"Recalculated statistics for session {frame.session_id} "
            f"after label correction on result {result_id}"
        )

    return {
        "result_id": result_id,
        "user_label": record.user_label,
        "ai_label": record.ai_label,
    }
