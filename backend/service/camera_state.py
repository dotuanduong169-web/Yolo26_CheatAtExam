"""Trạng thái camera dùng chung giữa capture loop và API.
Luồng chính: giữ một thể hiện duy nhất → API đọc/ghi cờ chạy, frame mới nhất, ca hiện tại."""

import threading
from collections import deque
from typing import Optional

import numpy as np

# Cửa sổ debounce gian lận: giữ tối đa 10 frame gần nhất để pipeline_service đối chiếu
CHEAT_WINDOW_MAXLEN = 10


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
        self.device_id: int | None = None
        # True/False gian lận từng frame gần nhất; snapshot chỉ ghi cheat đã xác nhận
        self.cheat_window: deque[bool] = deque(maxlen=CHEAT_WINDOW_MAXLEN)
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
        self.device_id = None
        self.cheat_window.clear()

    def note_frame_cheat(self, has_cheat: bool) -> None:
        """Ghi nhận frame hiện tại có/không có gian lận vào cửa sổ debounce."""
        self.cheat_window.append(bool(has_cheat))

    def is_cheat_confirmed(self, window: int = 5, min_hits: int = 3) -> bool:
        """True khi có ít nhất min_hits frame gian lận trong window frame gần nhất.
        Lọc phát hiện thoáng qua (false positive đơn lẻ) khỏi bản ghi snapshot."""
        recent = list(self.cheat_window)[-window:]
        return len(recent) >= min_hits and sum(recent) >= min_hits

    def is_running(self) -> bool:
        """Trả True khi capture loop đang chạy."""
        return self.running

    def __repr__(self) -> str:
        return (
            f"CameraState(running={self.running}, "
            f"session_id={self.current_session_id}, "
            f"frame_count={self.frame_count})"
        )