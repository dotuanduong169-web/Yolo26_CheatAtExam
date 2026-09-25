"""Schema kết quả AI cho nhãn phát hiện và sửa nhãn thủ công.
Logic chính: nhãn gian lận gồm Cheat_Paper và cellphone, user_label do người sửa ưu tiên hơn ai_label.
"""

from typing import Optional

from pydantic import BaseModel, Field


class AIResultResponse(BaseModel):
    """Bản ghi kết quả AI đầy đủ, confidence giới hạn từ 0 tới 1."""

    result_id: int
    temporary_student_id: str
    ai_label: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    face_bbox: str
    frame_id: int

    model_config = {"from_attributes": True}


class AIResultUpdate(BaseModel):
    """Dữ liệu sửa nhãn, status là nhãn chốt do người dùng xác nhận."""

    status: str = Field(..., min_length=1, max_length=100)


class AIResultUpdateResponse(BaseModel):
    """Phản hồi sau khi sửa nhãn, giữ cả nhãn AI gốc và nhãn người dùng để đối chiếu."""

    result_id: int
    user_label: Optional[str] = None
    ai_label: Optional[str] = None
