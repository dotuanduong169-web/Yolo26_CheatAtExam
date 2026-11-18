"""Schema thống kê cho tổng hợp ngày, tuần và dashboard.
Logic chính: sleeping là số vật gian lận (Cheat_Paper và cellphone), focus_rate là tỉ lệ bài sạch.
Lưu ý: tên key sleeping/focus_rate là lịch sử, giữ nguyên để tương thích DB và API.
"""

from datetime import datetime
from typing import Optional

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
    # Key mới cho frontend (giữ key cũ để tương thích ngược)
    total_sessions: int = 0
    total_cheats: int = 0
    clean_rate: float = 100.0
    most_common_behavior: str = "Chưa có vi phạm"


class TimelineCandidateInfo(BaseModel):
    """Thông tin thí sinh gắn với một tick/cảnh báo."""

    PK_MaThiSinh: int
    SBD: str
    HoTen: str
    Lop: Optional[str] = None

    model_config = {"from_attributes": True}


class TimelineSessionInfo(BaseModel):
    """Phiên con + ca thi cha của tick."""

    PK_MaPhienGiamSat: int
    parent_session_id: Optional[int] = None
    PhongThi: Optional[str] = None
    MonThi: Optional[str] = None


class TimelineItem(BaseModel):
    """Một mốc quan sát có ảnh, thời gian, thí sinh và trạng thái xác minh."""

    PK_MaDong: int
    thoi_gian: datetime
    co_canh_bao: bool
    camera: str = "front"
    phat_hien: list[dict] = []
    hanh_vi: str = ""
    do_tin_cay: Optional[float] = None
    trang_thai: Optional[str] = None
    event_id: Optional[int] = None
    do_tre_ms: Optional[int] = None
    image_url: Optional[str] = None
    image_b64: Optional[str] = None
    candidate: Optional[TimelineCandidateInfo] = None
    session: Optional[TimelineSessionInfo] = None


class TimelinePage(BaseModel):
    """Trang timeline cảnh báo của tất cả thí sinh."""

    total: int
    skip: int = 0
    limit: int = 30
    items: list[TimelineItem] = []


class CandidateStatItem(BaseModel):
    """Tổng hợp cảnh báo của một thí sinh."""

    candidate: TimelineCandidateInfo
    session_id: Optional[int] = None
    total_events: int = 0
    pending_events: int = 0
    timeline_alerts: int = 0
    last_alert_at: Optional[datetime] = None
    last_event_id: Optional[int] = None
    last_evidence_id: Optional[int] = None


class StatsOverviewResponse(BaseModel):
    """KPI thống kê đúng nghĩa thí sinh + cảnh báo + độ trễ."""

    total_students: int = 0
    students_with_alerts: int = 0
    total_timeline_alerts: int = 0
    total_events: int = 0
    pending_events: int = 0
    clean_rate: float = 1.0
    avg_latency_ms: Optional[float] = None
    max_latency_ms: Optional[int] = None
