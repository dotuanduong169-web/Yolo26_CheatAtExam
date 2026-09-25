"""
Schemas package — Pydantic models for request/response validation.

Re-exports all schemas for convenient imports::

    from schemas import UserCreate, SessionResponse
"""

from schemas.common import MessageResponse, TokenResponse

from schemas.user import (
    ChangePassword,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)

from schemas.session import (
    SessionDetailResponse,
    SessionFrameItem,
    SessionListItem,
    SessionResponse,
    SessionSummaryResponse,
)

from schemas.frame import (
    DetectionItem,
    FrameAnalysisItem,
    FrameDetailResponse,
    FrameResponse,
)

from schemas.ai_result import (
    AIResultResponse,
    AIResultUpdate,
    AIResultUpdateResponse,
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
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "UserUpdate",
    # Session
    "SessionDetailResponse",
    "SessionFrameItem",
    "SessionListItem",
    "SessionResponse",
    "SessionSummaryResponse",
    # Frame
    "DetectionItem",
    "FrameAnalysisItem",
    "FrameDetailResponse",
    "FrameResponse",
    # AI Result
    "AIResultResponse",
    "AIResultUpdate",
    "AIResultUpdateResponse",
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
