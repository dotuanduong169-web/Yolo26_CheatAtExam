"""Trạng thái camera dùng chung giữa capture loop và API.
Luồng chính: giữ một thể hiện duy nhất → API đọc/ghi cờ chạy, frame mới nhất, ca hiện tại."""

import os
import threading
from collections import deque
from typing import Optional

import numpy as np

# Cửa sổ debounce gian lận: giữ tối đa 12 frame gần nhất
CHEAT_WINDOW_MAXLEN = 12

# Ngưỡng debounce:
# Object (điện thoại, tài liệu): cần 3/5 frame (~0.8 - 1.2s)
OBJECT_WINDOW = 5
OBJECT_MIN_HITS = 3
# Pose (quay đầu, cúi xuống): cần 4/6 frame (~1.2 - 1.8s) để loại trừ cử động vô thức
POSE_WINDOW = 6
POSE_MIN_HITS = 4

# Cooldown chống spam giữa các lần lưu cùng vi phạm:
# Object: 15s (vật thể nằm yên, nhắc lại sau 15s nếu vẫn còn)
# Pose: 6s (hành vi diễn ra theo đợt ngắn 2-4s)
OBJECT_COOLDOWN_SECONDS = float(os.getenv("OBJECT_COOLDOWN_SECONDS", "15"))
POSE_COOLDOWN_SECONDS = float(os.getenv("POSE_COOLDOWN_SECONDS", "6"))


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
        # Luồng live: capture ghi raw_frame liên tục, worker infer ghi annotated + results
        self.raw_frame: Optional[np.ndarray] = None
        self.latest_results: list = []
        # Vài cặp (frame, results) gần nhất để snapshot chọn frame có cheat
        self.recent: deque = deque(maxlen=CHEAT_WINDOW_MAXLEN)
        self.lock = threading.Lock()
        # True/False gian lận từng frame gần nhất; snapshot chỉ ghi cheat đã xác nhận
        self.cheat_window: deque[bool] = deque(maxlen=CHEAT_WINDOW_MAXLEN)
        self.behavior_window: deque[bool] = deque(maxlen=CHEAT_WINDOW_MAXLEN)
        self.fps: float = 0.0
        self._fps_last_time: float = 0.0
        self._fps_last_count: int = 0
        self.start_time: Optional[float] = None

        # Quản lý cooldown riêng cho Object và Pose
        self.last_object_save_time: float = 0.0
        self.last_pose_save_time: float = 0.0
        self.last_stats_time: float = 0.0

        self._initialized = True

    def reset(self) -> None:
        """Đưa mọi trường về giá trị ban đầu sau khi dừng camera."""
        self.cap = None
        self.running = False
        self.thread = None
        self.current_session_id = None
        self.start_time = None
        self.latest_frame = None
        self.frame_count = 0
        self.source = None
        self.loop_video = False
        self.device_id = None
        self.raw_frame = None
        self.latest_results = []
        self.fps = 0.0
        self._fps_last_time = 0.0
        self._fps_last_count = 0
        self.recent.clear()
        self.cheat_window.clear()
        self.behavior_window.clear()
        self.last_object_save_time = 0.0
        self.last_pose_save_time = 0.0
        self.last_stats_time = 0.0
        try:
            from ai_model.ai_pipeline import reset_tracker
            reset_tracker()
        except Exception:
            pass

    def update_fps(self) -> None:
        """Tính toán FPS thời gian thực dựa trên số khung hình xử lý."""
        import time
        now = time.time()
        if self._fps_last_time == 0.0:
            self._fps_last_time = now
            self._fps_last_count = self.frame_count
            return
        dt = now - self._fps_last_time
        if dt >= 1.0:
            df = self.frame_count - self._fps_last_count
            self.fps = round(df / dt, 1)
            self._fps_last_time = now
            self._fps_last_count = self.frame_count

    def note_frame_cheat(self, has_cheat: bool) -> None:
        """Ghi nhận frame hiện tại có/không có gian lận vào cửa sổ debounce."""
        self.cheat_window.append(bool(has_cheat))

    def is_cheat_confirmed(self, window: int = OBJECT_WINDOW, min_hits: int = OBJECT_MIN_HITS) -> bool:
        """True khi có ít nhất min_hits frame gian lận trong window frame gần nhất."""
        recent = list(self.cheat_window)[-window:]
        return len(recent) >= min_hits and sum(recent) >= min_hits

    def note_frame_behavior(self, has_behavior: bool) -> None:
        """Ghi nhận frame có/không có hành vi gian lận (quay/cúi) để debounce riêng."""
        self.behavior_window.append(bool(has_behavior))

    def is_behavior_confirmed(self, window: int = POSE_WINDOW, min_hits: int = POSE_MIN_HITS) -> bool:
        """True khi hành vi gian lận lặp lại đủ trong cửa sổ (chống FP pose)."""
        recent = list(self.behavior_window)[-window:]
        return len(recent) >= min_hits and sum(recent) >= min_hits

    def check_triggers(self, results: list[dict], now: float) -> tuple[bool, list[dict], str]:
        """
        Đánh giá frame hiện tại: kiểm tra debounce và cooldown riêng cho Object và Pose.
        Trả về: (should_save, confirmed_results, reason)
        """
        has_obj = any(r.get("is_cheat") and r.get("kind", "object") == "object" for r in results)
        has_beh = any(r.get("is_cheat") and r.get("kind") == "behavior" for r in results)

        self.note_frame_cheat(has_obj)
        self.note_frame_behavior(has_beh)

        trigger_obj = False
        trigger_beh = False

        if has_obj and self.is_cheat_confirmed(OBJECT_WINDOW, OBJECT_MIN_HITS):
            if now - self.last_object_save_time >= OBJECT_COOLDOWN_SECONDS:
                trigger_obj = True
                self.last_object_save_time = now

        if has_beh:
            is_quay_sau = any(r.get("label") == "quay_sau" for r in results)
            beh_ok = self.is_behavior_confirmed(4, 3) if is_quay_sau else self.is_behavior_confirmed(POSE_WINDOW, POSE_MIN_HITS)
            if beh_ok and (now - self.last_pose_save_time >= POSE_COOLDOWN_SECONDS):
                trigger_beh = True
                self.last_pose_save_time = now

        if not (trigger_obj or trigger_beh):
            return False, [], ""

        confirmed = []
        reasons = []
        if trigger_obj:
            reasons.append("object")
            confirmed.extend([r for r in results if r.get("is_cheat") and r.get("kind", "object") == "object"])
        if trigger_beh:
            reasons.append("behavior")
            confirmed.extend([r for r in results if r.get("is_cheat") and r.get("kind") == "behavior"])

        return True, confirmed, "+".join(reasons)

    def is_running(self) -> bool:
        """Trả True khi capture loop đang chạy."""
        return self.running

    def __repr__(self) -> str:
        return (
            f"CameraState(running={self.running}, "
            f"session_id={self.current_session_id}, "
            f"frame_count={self.frame_count})"
        )