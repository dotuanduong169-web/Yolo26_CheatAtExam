"""Gói schema Pydantic. Logic: re-export để import gọn từ schemas."""

from schemas.common import MessageResponse, TokenResponse

from schemas.user import (
    ChangePassword,
    UserAdminUpdate,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)

from schemas.device import (
    DeviceCreate,
    DeviceResponse,
    DeviceUpdate,
)

from schemas.session import (
    SessionCreate,
    SessionDetailResponse,
    SessionListItem,
    SessionResponse,
    SessionSummaryResponse,
)

from schemas.event import (
    EventResponse,
    EventVerify,
    EvidenceResponse,
)

from schemas.statistics import (
    DailyStatItem,
    DateStatItem,
    StatisticResponse,
    StatsSummaryResponse,
    WeeklyStatItem,
)

from schemas.camera import (
    CameraDevice,
    CameraInfoResponse,
    CameraListResponse,
    CameraStartResponse,
    CameraStatusResponse,
    CameraStopResponse,
)

__all__ = [
    # Common
    "MessageResponse",
    "TokenResponse",
    # User
    "ChangePassword",
    "UserAdminUpdate",
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "UserUpdate",
    # Device
    "DeviceCreate",
    "DeviceResponse",
    "DeviceUpdate",
    # Session
    "SessionCreate",
    "SessionDetailResponse",
    "SessionListItem",
    "SessionResponse",
    "SessionSummaryResponse",
    # Event
    "EventResponse",
    "EventVerify",
    "EvidenceResponse",
    # Statistics
    "DailyStatItem",
    "DateStatItem",
    "StatisticResponse",
    "StatsSummaryResponse",
    "WeeklyStatItem",
    # Camera
    "CameraDevice",
    "CameraInfoResponse",
    "CameraListResponse",
    "CameraStartResponse",
    "CameraStatusResponse",
    "CameraStopResponse",
]
