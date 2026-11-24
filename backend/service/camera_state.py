"""Trạng thái camera dùng chung giữa capture loop và API.
Luồng chính: giữ một thể hiện duy nhất → API đọc/ghi cờ chạy, frame mới nhất, ca hiện tại."""

import os
import threading
from collections import deque
from typing import Optional

import numpy as np

# Kiến trúc Snapshot định kỳ (2.5s / snapshot):
# Kích hoạt tức thì theo từng snapshot (1/1 frame) thay vì đệm trượt như video stream 30 FPS cũ.
CHEAT_WINDOW_MAXLEN = 5

OBJECT_WINDOW = 1
OBJECT_MIN_HITS = 1
POSE_WINDOW = 1
POSE_MIN_HITS = 1

# Cooldown chống spam giữa các lần lưu cùng vi phạm:
# Object: 15s (tương đương 6 chu kỳ snapshot 2.5s)
# Pose: 6s (tương đương 2-3 chu kỳ snapshot 2.5s)
OBJECT_COOLDOWN_SECONDS = float(os.getenv("OBJECT_COOLDOWN_SECONDS", "15.0"))
POSE_COOLDOWN_SECONDS = float(os.getenv("POSE_COOLDOWN_SECONDS", "6.0"))


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

        # Cooldown theo từng nhãn (không dùng chung một mốc cho mọi vật/hành vi,
        # vì cellphone sẽ chặn Cheat_Paper và quay_dau sẽ chặn cui_xuong).
        self.last_save_by_label: dict[str, float] = {}
        # Giữ 2 mốc cũ để tương thích với mã bên ngoài từng đọc trực tiếp.
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
        self.last_save_by_label.clear()
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

    @staticmethod
    def _cooldown_seconds(label: str) -> float:
        """Vật thể dùng cooldown 15s, hành vi dùng 6s (theo từng nhãn)."""
        if label in {"Cheat_Paper", "cellphone"}:
            return OBJECT_COOLDOWN_SECONDS
        return POSE_COOLDOWN_SECONDS

    def _label_due(self, label: str, now: float) -> bool:
        last = self.last_save_by_label.get(label, 0.0)
        return now - last >= self._cooldown_seconds(label)

    def check_triggers(self, results: list[dict], now: float) -> tuple[bool, list[dict], str]:
        """
        Đánh giá frame hiện tại: debounce + cooldown RIÊNG theo từng nhãn.
        Trả về: (should_save, confirmed_results, reason)

        Một nhãn đang cooldown không được chặn nhãn khác, và không được tự động
        lưu lại chỉ vì "có cheat khác" trong frame.
        """
        has_obj = any(r.get("is_cheat") and r.get("kind", "object") == "object" for r in results)
        has_beh = any(r.get("is_cheat") and r.get("kind") == "behavior" for r in results)

        self.note_frame_cheat(has_obj)
        self.note_frame_behavior(has_beh)

        confirmed: list[dict] = []
        reasons: list[str] = []

        due_obj = [
            r for r in results
            if r.get("is_cheat")
            and r.get("kind", "object") == "object"
            and self._label_due(str(r.get("label") or ""), now)
        ]
        if has_obj and due_obj and self.is_cheat_confirmed(OBJECT_WINDOW, OBJECT_MIN_HITS):
            confirmed.extend(due_obj)
            reasons.append("object")
            for r in due_obj:
                self.last_save_by_label[str(r.get("label") or "")] = now
            self.last_object_save_time = now

        due_beh = [
            r for r in results
            if r.get("is_cheat")
            and r.get("kind") == "behavior"
            and self._label_due(str(r.get("label") or ""), now)
        ]
        if has_beh and due_beh and self.is_behavior_confirmed(POSE_WINDOW, POSE_MIN_HITS):
            beh_confirmed = [
                r for r in due_beh
                if r.get("label") == "quay_sau"
                or self.is_behavior_confirmed(POSE_WINDOW, POSE_MIN_HITS)
            ]
            if beh_confirmed:
                confirmed.extend(beh_confirmed)
                reasons.append("behavior")
                for r in beh_confirmed:
                    self.last_save_by_label[str(r.get("label") or "")] = now
                self.last_pose_save_time = now

        if not confirmed:
            return False, [], ""
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