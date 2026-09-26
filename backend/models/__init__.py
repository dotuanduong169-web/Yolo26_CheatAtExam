"""Gói model ORM. Logic: import đủ model để đăng ký Base trước khi tạo bảng."""

from database.database import Base

from models.user import User
from models.edgedevice import EdgeDevice
from models.monitoring_session import MonitoringSession
from models.detected_event import DetectedEvent
from models.evidence import Evidence
from models.statistic import Statistic

__all__ = [
    "Base",
    "User",
    "EdgeDevice",
    "MonitoringSession",
    "DetectedEvent",
    "Evidence",
    "Statistic",
]
