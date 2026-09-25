"""Schema thống kê cho tổng hợp ngày, tuần và dashboard.
Logic chính: sleeping là số vật gian lận (Cheat_Paper và cellphone), focus_rate là tỉ lệ bài sạch.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class StatisticResponse(BaseModel):
    """Một bản ghi thống kê, focus_rate giới hạn từ 0 tới 1."""

    statistic_id: int
    timestamp: datetime
    total_students: int = Field(..., ge=0)
    sleeping_count: int = Field(..., ge=0)
    focus_rate: float = Field(..., ge=0.0, le=1.0)
    session_id: int

    model_config = {"from_attributes": True}


class DailyStatItem(BaseModel):
    """Thống kê gom theo một ngày, sleeping là tổng vật gian lận trong ngày."""

    date: str
    total: int
    sleeping: int
    focus_rate: float


class WeeklyStatItem(BaseModel):
    """Thống kê gom theo một tuần cho biểu đồ xu hướng."""

    week: str
    total: int
    focus_rate: float


class DateStatItem(BaseModel):
    """Số vật gian lận của một ngày cụ thể cho biểu đồ cảnh báo."""

    date: str
    value: int


class StatsSummaryResponse(BaseModel):
    """Tổng hợp toàn hệ thống cho dashboard, sleeping_alerts là tổng vật gian lận."""

    total_records: int
    total_students: int
    avg_focus_rate: float
    sleeping_alerts: int
