"""Trạng thái camera dùng chung giữa capture loop và API.
Luồng chính: giữ một thể hiện duy nhất → API đọc/ghi cờ chạy, frame mới nhất, ca hiện tại."""

import threading
from typing import Optional

import numpy as np


class CameraState:
    """Bộ nhớ dùng chung của camera, an toàn luồng nhờ khóa khi khởi tạo.
    Điểm logic: chỉ tạo một thể hiện duy nhất; cờ loop_video cho phép video file chạy lặp."""

    _instance: Optional["CameraState"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "CameraState":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self.cap = None
        self.running: bool = False
        self.thread: Optional[threading.Thread] = None
        self.current_session_id: Optional[int] = None
        self.latest_frame: Optional[np.ndarray] = None
        self.frame_count: int = 0
        self.source: str | None = None
        self.loop_video: bool = False
        self._initialized = True

    def reset(self) -> None:
        """Đưa mọi trường về giá trị ban đầu sau khi dừng camera."""
        self.cap = None
        self.running = False
        self.thread = None
        self.current_session_id = None
        self.latest_frame = None
        self.frame_count = 0
        self.source = None
        self.loop_video = False

    def is_running(self) -> bool:
        """Trả True khi capture loop đang chạy."""
        return self.running

    def __repr__(self) -> str:
        return (
            f"CameraState(running={self.running}, "
            f"session_id={self.current_session_id}, "
            f"frame_count={self.frame_count})"
        )