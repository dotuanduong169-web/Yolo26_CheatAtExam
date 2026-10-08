"""Vòng lặp capture: đọc camera hoặc video file, chạy YOLO26-seg, lưu DB.
Luồng chính: capture đọc liên tục → worker infer riêng vẽ box live → định kỳ lưu 1 ảnh + sự kiện."""

import os
import threading
import time
from datetime import datetime
from pathlib import Path

import cv2

from ai_model.ai_pipeline import process_frame
from core.config import settings
from core.logger import get_logger
from crud.event_crud import create_event, create_evidence
from crud.statistics_crud import create_statistics
from database.database import SessionLocal
from service.camera_state import CameraState

logger = get_logger(__name__)

# Chu kỳ lưu snapshot: 10 giây một ảnh kèm sự kiện và thống kê (chỉnh qua SAVE_INTERVAL_SECONDS).
# 10 giây đủ nhanh để sự kiện lên list kịp lúc, vẫn tránh spam ảnh/sự kiện khi vật đứng yên.
SAVE_INTERVAL_SECONDS = int(os.getenv("SAVE_INTERVAL_SECONDS", "10"))
# Debounce gian lận: cheat chỉ ghi sự kiện khi có >=3 frame gian lận trong 5 frame gần nhất
CHEAT_WINDOW = 5
CHEAT_MIN_HITS = 3


def capture_loop() -> None:
    """
    Vòng lặp capture chính, chạy trong luồng nền.
    Điểm logic: đọc frame liên tục (không chờ infer) → worker infer riêng vẽ box;
    lưu DB định kỳ; video hết thì tua lại, camera mất thì chờ 0,2 giây.
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

    worker = threading.Thread(target=_infer_worker, args=(state,), daemon=True)
    worker.start()

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
                state.update_fps()
                # Chỉ giao frame mới nhất cho worker, không chờ infer xong
                state.raw_frame = frame

                # Định kỳ lưu thống kê phiên (stats) cho biểu đồ giám sát
                if time.time() - last_save_time > SAVE_INTERVAL_SECONDS:
                    with state.lock:
                        results = list(state.latest_results)
                    _save_periodic_stats(db, state.current_session_id, results)
                    last_save_time = time.time()

            except KeyboardInterrupt:
                logger.info("Capture loop interrupted by user")
                break
            except Exception as exc:
                logger.error(f"Error in capture loop: {exc}", exc_info=True)
                continue

    except Exception as exc:
        logger.critical(f"Fatal error in capture loop: {exc}", exc_info=True)
    finally:
        try:
            if state.current_session_id:
                from crud.session_crud import end_session
                end_session(db, state.current_session_id)
        except Exception as exc_end:
            logger.warning(f"Failed to end session #{state.current_session_id} on loop exit: {exc_end}")
        db.close()
        logger.info("Capture loop stopped")


def _infer_worker(state: CameraState) -> None:
    """Worker infer liên tục frame mới nhất.
    Điểm logic: luôn lấy raw_frame hiện tại; vẽ box xong cập nhật latest_frame;
    kiểm tra debounce và cooldown để lưu sự kiện vi phạm NGAY LẬP TỨC (Event-driven)
    thay vì chờ chu kỳ 10s cố định, giúp không bao giờ bỏ sót hành vi pose ngắn hạn."""
    last_id = None
    db_worker = None
    try:
        db_worker = SessionLocal()
    except Exception as exc:
        logger.error(f"Infer worker failed to connect DB: {exc}")

    image_dir = settings.IMAGE_DIR
    try:
        image_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

    while state.running:
        try:
            raw = state.raw_frame
            if raw is None or id(raw) == last_id:
                time.sleep(0.02)
                continue
            last_id = id(raw)

            annotated, results = process_frame(raw.copy(), state.frame_count)
            with state.lock:
                state.latest_frame = annotated
                state.latest_results = results
                state.recent.append((annotated, results))

            # Kích hoạt lưu bằng chứng NGAY LẬP TỨC khi vi phạm được xác nhận & hết cooldown
            now = time.time()
            should_save, confirmed_cheats, reason = state.check_triggers(results, now)
            if should_save and state.current_session_id and db_worker is not None:
                _save_event_snapshot(
                    db_worker,
                    state.current_session_id,
                    annotated,
                    confirmed_cheats,
                    image_dir,
                    state.frame_count,
                    reason=reason,
                )
        except Exception as exc:
            logger.debug(f"Infer worker failed: {exc}")
        time.sleep(0.04)

    if db_worker is not None:
        try:
            db_worker.close()
        except Exception:
            pass


def _keep_result(state: CameraState, r: dict) -> bool:
    """Quyết định giữ detection vào snapshot.
    Điểm logic: vật sạch luôn giữ; vật gian lận cần debounce 3/5;
    hành vi quay/cúi cần debounce riêng; quay_sau ghi ngay."""
    if not r.get("is_cheat"):
        return True
    if r.get("kind") == "behavior":
        if r.get("label") == "quay_sau":
            return True
        return state.is_behavior_confirmed(CHEAT_WINDOW, CHEAT_MIN_HITS)
    return state.is_cheat_confirmed(CHEAT_WINDOW, CHEAT_MIN_HITS)


def _save_event_snapshot(
    db,
    session_id: int | None,
    frame,
    results: list[dict],
    image_dir: Path,
    frame_count: int,
    reason: str = "",
) -> None:
    """Lưu snapshot sự kiện vi phạm NGAY LẬP TỨC: 1 ảnh bằng chứng + 1 event/vật + cập nhật stats."""
    if not session_id or not results:
        return

    filename = datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".jpg"
    image_path = image_dir / filename

    try:
        cv2.imwrite(str(image_path), frame)
    except Exception as exc:
        logger.error(f"Failed to save event image: {exc}", exc_info=True)
        return

    try:
        saved_events = 0
        for r in results:
            if not r.get("is_cheat"):
                continue
            event = create_event(
                db,
                session_id=session_id,
                loai_hanh_vi=r.get("label", ""),
                nhan_ai=r.get("label", ""),
                toa_do=r.get("bbox", []),
                do_tin_cay=float(r.get("confidence", 0.0)),
            )
            create_evidence(db, event.PK_MaSuKien, "anh", str(image_path))
            saved_events += 1

        stats_data = calculate_stats(results)
        create_statistics(db, stats_data, session_id)

        db.commit()
        logger.info(
            f"Event snapshot saved [{reason}] — frame #{frame_count}, events: {saved_events}, file: {filename}"
        )
    except Exception as exc:
        db.rollback()
        logger.error(f"Failed to save event snapshot transaction: {exc}", exc_info=True)


def _save_periodic_stats(
    db,
    session_id: int | None,
    results: list[dict],
) -> None:
    """Định kỳ ghi bản ghi thống kê Statistic (không ghi ảnh thừa khi không có vi phạm mới)."""
    if not session_id:
        return
    try:
        stats_data = calculate_stats(results)
        create_statistics(db, stats_data, session_id)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.debug(f"Failed to save periodic statistics: {exc}")


def _save_snapshot(
    db,
    session_id: int | None,
    frame,
    results: list[dict],
    image_dir: Path,
    frame_count: int,
) -> None:
    """Lưu snapshot định kỳ tương thích ngược (dùng cho ingest online)."""
    cheats = [r for r in results if r.get("is_cheat")]
    if cheats:
        _save_event_snapshot(db, session_id, frame, cheats, image_dir, frame_count, reason="snapshot")
    else:
        _save_periodic_stats(db, session_id, results)


def calculate_stats(results: list[dict]) -> dict:
    """
    Thống kê gian lận của một snapshot.
    total: tổng số detection; sleeping: số lượng vi phạm gian lận;
    focus_rate: 1.0 nếu sạch (không vi phạm), 0.0 nếu có vi phạm.
    """
    total = len(results)
    cheat_count = sum(1 for r in results if r.get("is_cheat"))
    clean_rate = 1.0 if cheat_count == 0 else 0.0

    return {"total": total, "sleeping": cheat_count, "focus_rate": clean_rate}
