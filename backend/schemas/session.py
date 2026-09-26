"""Schema ca thi cho lịch sử, chi tiết và tổng hợp dashboard.
Logic chính: sleeping là số vật gian lận (Cheat_Paper và cellphone), focus_rate là tỉ lệ bài sạch.
Lưu ý: tên key sleeping/focus_rate là lịch sử, giữ nguyên để tương thích DB và API.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SessionResponse(BaseModel):
    """Bản ghi session đầy đủ, đọc trực tiếp từ model DB."""

    session_id: int
    class_id: str = Field(..., min_length=1, max_length=100)
    start_time: datetime
    end_time: Optional[datetime] = None
    camera_url: str
    user_id: Optional[int] = None

    model_config = {"from_attributes": True}


class SessionListItem(BaseModel):
    """Dòng session gọn nhẹ cho danh sách lịch sử, kèm số frame đã trích xuất."""

    session_id: int
    class_id: str
    date: str
    frame_count: int


class SessionFrameItem(BaseModel):
    """Tóm tắt một frame trong màn chi tiết session, sleeping là số vật gian lận."""

    frame_id: int
    time: str
    status: str
    students: int
    accuracy: float
    sleeping: int


class SessionDetailResponse(BaseModel):
    """Chi tiết session kèm tổng hợp và danh sách frame, is_active cho biết ca đang chạy."""

    session_id: int
    class_id: str
    total_students: int
    sleeping: int
    focus_rate: float
    alerts: int
    duration: int  # phút
    is_active: bool
    frames: list[SessionFrameItem]

    model_config = {"from_attributes": True}


class SessionSummaryResponse(BaseModel):
    """Tổng số ca thi và số ca trong tháng cho dashboard."""

    total_sessions: int
    month_sessions: int
