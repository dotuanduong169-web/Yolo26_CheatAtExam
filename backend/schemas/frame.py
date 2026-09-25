"""Schema frame và kết quả phân tích từng frame.
Logic chính: sleeping_count là số vật gian lận (Cheat_Paper và cellphone), user_label sửa tay ưu tiên hơn nhãn AI.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class FrameResponse(BaseModel):
    """Bản ghi frame cơ bản, đọc trực tiếp từ model DB."""

    frame_id: int
    image_path: str
    extracted_at: datetime
    session_id: int

    model_config = {"from_attributes": True}


class FrameAnalysisItem(BaseModel):
    """Frame kèm số bài sạch và số vật gian lận đã tính sẵn cho biểu đồ."""

    frame_id: int
    image_path: str
    extracted_at: datetime
    focus_count: int
    sleeping_count: int
    total_students: int


class DetectionItem(BaseModel):
    """Một vật phát hiện trong frame, status đã chốt theo user_label nếu người dùng sửa."""

    result_id: int
    student_id: str
    status: str
    confidence: float
    user_label: Optional[str] = None
    face_bbox: Optional[list[int]] = None


class FrameDetailResponse(BaseModel):
    """Chi tiết đầy đủ của một frame kèm toàn bộ vật phát hiện."""

    frame_id: int
    session_id: int
    image_path: str
    total_students: int
    sleeping_count: int
    focus_count: int
    avg_confidence: float
    detections: list[DetectionItem]
