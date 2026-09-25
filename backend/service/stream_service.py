"""Phát luồng MJPEG cho video trực tiếp.
Luồng chính: lấy frame mới nhất → nén JPEG → đẩy về trình duyệt ở 15 FPS."""

import time

import cv2

from service.camera_state import CameraState

# Chất lượng JPEG 65 để nhẹ băng thông; trần 15 FPS để đỡ tốn CPU trình duyệt
JPEG_QUALITY = 65
TARGET_FPS = 15
_FRAME_INTERVAL = 1.0 / TARGET_FPS


def gen_frames():
    """
    Sinh các frame MJPEG từ trạng thái camera cho endpoint video_feed.
    Điểm logic: throttle ở 15 FPS, bỏ qua frame trùng, co ngang về tối đa 720px.
    """
    state = CameraState()
    last_send_time = 0.0
    prev_frame_id = None  # Ghi nhớ frame cũ để bỏ qua frame trùng

    while state.running:
        if state.latest_frame is None:
            time.sleep(0.05)
            continue

        # Hãm tốc độ gửi về đúng 15 FPS
        now = time.time()
        elapsed = now - last_send_time
        if elapsed < _FRAME_INTERVAL:
            time.sleep(_FRAME_INTERVAL - elapsed)

        # Frame chưa đổi thì bỏ qua để khỏi mã hóa thừa
        current_id = id(state.latest_frame)
        if current_id == prev_frame_id:
            time.sleep(0.01)
            continue
        prev_frame_id = current_id

        # Co nhỏ frame về ngang tối đa 720px cho nhẹ luồng phát
        frame = state.latest_frame
        h, w = frame.shape[:2]
        if w > 720:
            scale = 720 / w
            frame = cv2.resize(frame, (720, int(h * scale)))

        ret, buffer = cv2.imencode(
            ".jpg",
            frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY],
        )
        if not ret:
            continue

        last_send_time = time.time()
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + buffer.tobytes()
            + b"\r\n"
        )
