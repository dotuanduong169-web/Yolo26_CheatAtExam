"""Gói model ORM. Logic: import đủ model để đăng ký Base trước khi tạo bảng."""

from database.database import Base

from models.user import User
from models.edgedevice import EdgeDevice
from models.candidate import Candidate
from models.monitoring_session import MonitoringSession
from models.camera_stream import CameraStream
from models.snapshot import Snapshot, SnapshotProcessed
from models.detected_event import DetectedEvent
from models.evidence import Evidence

__all__ = [
    "Base",
    "User",
    "EdgeDevice",
    "Candidate",
    "MonitoringSession",
    "CameraStream",
    "Snapshot",
    "SnapshotProcessed",
    "DetectedEvent",
    "Evidence",
]
