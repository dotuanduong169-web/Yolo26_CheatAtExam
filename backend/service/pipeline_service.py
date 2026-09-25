"""Vòng lặp capture: đọc camera hoặc video file, chạy YOLO26-seg, lưu DB.
Luồng chính: đọc frame → infer → lưu snapshot mỗi 30 giây."""

import time
from datetime import datetime
from pathlib import Path

import cv2

from ai_model.ai_pipeline import is_cheat_label, process_frame
from core.config import settings
from core.logger import get_logger
from crud.ai_result_crud import create_ai_result
from crud.frame_crud import create_frame
from crud.statistics_crud import create_statistics
from database.database import SessionLocal
from service.camera_state import CameraState

logger = get_logger(__name__)

# Chu kỳ lưu snapshot: 30 giây một ảnh kèm kết quả và thống kê
SAVE_INTERVAL_SECONDS = 30


def capture_loop() -> None:
    """
    Vòng lặp capture chính, chạy trong luồng nền.
    Điểm logic: đọc frame → infer YOLO26-seg → lưu DB mỗi 30 giây;
    video hết thì tua lại từ đầu, camera mất thì chờ 0,2 giây rồi đọc tiếp.
    """
    state = CameraState()

    try:
        db = SessionLocal()
        logger.info("Database connection established for capture loop")
    except Exception as exc:
        logger.error(f"Database connection failed: {exc}", exc_info=True)
        return

    image_dir = settings.IMAGE_DIR
    try:
        image_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.error(f"Failed to create image directory: {exc}", exc_info=True)
        return

    last_save_time = 0.0
    frame_count = 0

    logger.info("Capture loop started")

    try:
        while state.running:
            try:
                ret, frame = state.cap.read()
                if not ret:
                    # Video hết thì tua lại từ đầu, camera mất thì chờ đọc tiếp
                    if getattr(state, "loop_video", False) and getattr(state, "source", None):
                        try:
                            state.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            continue
                        except Exception:
                            pass
                        logger.info("Video ended — stopping (loop disabled on error)")
                        state.running = False
                        break
                    logger.warning("Failed to read frame from source")
                    time.sleep(0.2)
                    continue

                state.frame_count += 1
                frame_count += 1

                # Chạy infer AI trên frame hiện tại
                processed_frame, results = process_frame(frame, state.frame_count)
                state.latest_frame = processed_frame

                # Đủ 30 giây thì lưu snapshot một lần
                if time.time() - last_save_time > SAVE_INTERVAL_SECONDS:
                    _save_snapshot(db, state, frame, results, image_dir, frame_count)
                    last_save_time = time.time()

                time.sleep(0.05)  # Nghỉ 0,05 giây để trần tốc độ khoảng 20 FPS

            except KeyboardInterrupt:
                logger.info("Capture loop interrupted by user")
                break
            except Exception as exc:
                logger.error(f"Error in capture loop: {exc}", exc_info=True)
                continue

    except Exception as exc:
        logger.critical(f"Fatal error in capture loop: {exc}", exc_info=True)
    finally:
        db.close()
        logger.info("Capture loop stopped")


def _save_snapshot(
    db,
    state: CameraState,
    frame,
    results: list[dict],
    image_dir: Path,
    frame_count: int,
) -> None:
    """Lưu một snapshot gồm ảnh frame, kết quả AI và thống kê vào DB.
    Điểm logic: thiếu ca hiện tại thì bỏ qua; lỗi thì rollback để không ghi dở."""
    filename = datetime.now().strftime("%Y%m%d_%H%M%S") + ".jpg"
    image_path = image_dir / filename

    try:
        cv2.imwrite(str(image_path), frame)
    except Exception as exc:
        logger.error(f"Failed to save image: {exc}", exc_info=True)
        return

    if not state.current_session_id:
        return

    try:
        frame_obj = create_frame(db, str(image_path), state.current_session_id)

        for r in results:
            create_ai_result(db, r, frame_obj.frame_id)

        stats_data = calculate_stats(results)
        create_statistics(db, stats_data, state.current_session_id)

        db.commit()
        logger.info(f"Snapshot saved — frames: {frame_count}, detections: {len(results)}")

    except Exception as exc:
        db.rollback()
        logger.error(f"Database transaction failed: {exc}", exc_info=True)


def calculate_stats(results: list[dict]) -> dict:
    """
    Thống kê gian lận của một snapshot, giữ key cũ để hợp schema DB mẫu.
    Điểm logic: gian lận là Cheat_Paper và cellphone;
    cheat-rate = 1 - gian lận/tổng, frame trắng thì coi như sạch hoàn toàn.
    """
    total = len(results)
    sleeping = sum(1 for r in results if is_cheat_label(r.get("label", "")))
    focus_rate = 1 - (sleeping / total) if total else 1.0

    return {"total": total, "sleeping": sleeping, "focus_rate": focus_rate}