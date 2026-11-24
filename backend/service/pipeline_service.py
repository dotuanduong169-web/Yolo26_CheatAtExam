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

# Chu kỳ lưu snapshot định kỳ khi không có vi phạm (heartbeat): 10 giây
SAVE_INTERVAL_SECONDS = int(os.getenv("SAVE_INTERVAL_SECONDS", "10"))
# Kiến trúc Snapshot: Kích hoạt tức thì theo từng snapshot (1/1)
CHEAT_WINDOW = 1
CHEAT_MIN_HITS = 1


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
    Với kiến trúc snapshot 2.5s, các phát hiện vi phạm được kích hoạt tức thì (1/1)."""
    return True


def _iou(a: list, b: list) -> float:
    """IoU 2 bbox [x1,y1,x2,y2]; bbox rỗng (hành vi) trả 0."""
    if len(a) < 4 or len(b) < 4:
        return 0.0
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - ix * iy
    return ix * iy / union if union > 0 else 0.0


def _dedupe_cheats(results: list[dict], iou_thr: float = 0.45) -> list[dict]:
    """Gộp các detection trùng nhãn + chồng lấn trong CÙNG một ảnh.

    Một chiếc điện thoại bị tracker tách thành 2-3 box, hoặc pose trả 2 box cho
    cùng một người, trước đây sinh 2-3 sự kiện trên cùng một ảnh bằng chứng.
    Hành vi không có bbox nên mỗi nhãn chỉ giữ 1 (box tin cậy cao nhất).
    """
    unique: list[dict] = []
    cheats = [r for r in results if r.get("is_cheat")]
    for r in sorted(cheats, key=lambda x: float(x.get("confidence") or 0.0), reverse=True):
        label = r.get("label")
        bbox = r.get("bbox") or []
        if any(
            k.get("label") == label
            and (
                r.get("kind") == "behavior"
                or not bbox
                or not (k.get("bbox") or [])
                or _iou(bbox, k.get("bbox") or []) >= iou_thr
            )
            for k in unique
        ):
            continue
        unique.append(r)
    return unique


def _save_event_snapshot(
    db,
    session_id: int | None,
    frame,
    results: list[dict],
    image_dir: Path,
    frame_count: int,
    reason: str = "",
    vai_tro_camera: str = "front",
) -> list[int]:
    """Lưu snapshot sự kiện vi phạm NGAY LẬP TỨC: 1 ảnh bằng chứng + 1 event/vật.
    Trả về danh sách PK_MaSuKien đã tạo để timeline tick liên kết."""
    if not session_id or not results:
        return []

    # Gộp box trùng trước khi ghi ảnh: tránh 1 ảnh nhưng 2-3 event cùng nhãn.
    results = _dedupe_cheats(results)
    if not results:
        return []

    # Tên file kèm phiên + vai trò để 2 luồng camera không ghi đè nhau và dễ truy vết.
    filename = (
        f"{session_id}_{vai_tro_camera}_"
        + datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        + ".jpg"
    )
    image_path = image_dir / filename

    try:
        cv2.imwrite(str(image_path), frame)
    except Exception as exc:
        logger.error(f"Failed to save event image: {exc}", exc_info=True)
        return []

    event_ids: list[int] = []
    try:
        saved_events = 0
        for r in results:
            if not r.get("is_cheat"):
                continue
            event = create_event(
                db,
                session_id=session_id,
                loai_hanh_vi=r.get("label", ""),
                toa_do=r.get("bbox", []),
                do_tin_cay=float(r.get("confidence", 0.0)),
                vai_tro_camera=vai_tro_camera,
            )
            create_evidence(
                db,
                event.PK_MaSuKien,
                "anh",
                str(image_path),
                vai_tro_camera=vai_tro_camera,
            )
            event_ids.append(event.PK_MaSuKien)
            saved_events += 1

        db.commit()
        logger.info(
            f"Event snapshot saved [{reason}] — frame #{frame_count}, events: {saved_events}, file: {filename}"
        )
        return event_ids
    except Exception as exc:
        db.rollback()
        logger.error(f"Failed to save event snapshot transaction: {exc}", exc_info=True)
        return []


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
    vai_tro_camera: str = "front",
) -> list[int]:
    """Lưu snapshot định kỳ tương thích ngược (dùng cho ingest online)."""
    cheats = [r for r in results if r.get("is_cheat")]
    if cheats:
        return _save_event_snapshot(
            db,
            session_id,
            frame,
            cheats,
            image_dir,
            frame_count,
            reason="snapshot",
            vai_tro_camera=vai_tro_camera,
        )
    # Chỉ camera trước ghi thống kê định kỳ: camera phụ chạy song song sẽ
    # nhân đôi số liệu trong bảng statistics của cùng một phiên.
    if vai_tro_camera == "front":
        _save_periodic_stats(db, session_id, results)
    return []


def calculate_stats(results: list[dict]) -> dict:
    """
    Thống kê gian lận của một snapshot.
    total: tổng số detection; sleeping: số lượng vi phạm gian lận;
    focus_rate: 1.0 nếu sạch (không vi phạm), 0.0 nếu có vi phạm.
    """
    total = len(results)
    cheat_count = sum(1 for r in results if r.get("is_cheat"))
    clean_rate = 1.0 if cheat_count == 0 else 0.0

