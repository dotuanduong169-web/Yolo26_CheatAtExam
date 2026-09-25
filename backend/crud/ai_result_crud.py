"""Quản lý kết quả phát hiện YOLO của từng frame.
Logic chính: nhãn gian lận gồm Cheat_Paper và cellphone, user_label do người sửa luôn ưu tiên hơn ai_label.
"""

from typing import Optional

from sqlalchemy.orm import Session as DBSession

from models.ai_result import AIResult


def create_ai_result(db: DBSession, data: dict, frame_id: int) -> AIResult:
    """Tạo kết quả phát hiện. Dùng flush để có ID trước commit cho snapshot thống kê."""
    ai = AIResult(
        temporary_student_id="unknown",
        face_bbox=str(data["bbox"]),
        ai_label=data["label"],
        confidence=data["confidence"],
        frame_id=frame_id,
    )
    db.add(ai)
    db.flush()
    return ai


def get_ai_results_by_frame(db: DBSession, frame_id: int) -> list[AIResult]:
    """Lấy toàn bộ kết quả AI của một frame."""
    return db.query(AIResult).filter(AIResult.frame_id == frame_id).all()


def get_ai_results_by_frames(db: DBSession, frame_ids: list[int]) -> list[AIResult]:
    """Lấy kết quả AI của nhiều frame. Gom một truy vấn IN để chống N+1, rỗng thì trả về ngay."""
    if not frame_ids:
        return []
    return db.query(AIResult).filter(AIResult.frame_id.in_(frame_ids)).all()


def update_ai_result_label(
    db: DBSession,
    result_id: int,
    user_label: str,
) -> Optional[AIResult]:
    """Ghi nhãn do người dùng sửa đè lên nhãn AI. Trả về None nếu bản ghi không tồn tại."""
    record = db.query(AIResult).filter(AIResult.result_id == result_id).first()
    if not record:
        return None

    record.user_label = user_label
    db.commit()
    db.refresh(record)
    return record
