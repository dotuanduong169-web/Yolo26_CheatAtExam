"""Suy luận YOLO26-seg 3 nhãn Answer_paper/Cheat_Paper/cellphone cho giám sát thi cử.
Luồng chính: đọc frame → infer một lần → vẽ khung và polygon rồi gắn cờ gian lận."""

import os
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

# Đường dẫn trọng số, cho phép ghi đè qua biến môi trường MODEL_PATH
_AI_MODEL_DIR = Path(__file__).resolve().parent
_DEFAULT_WEIGHTS = _AI_MODEL_DIR / "weights" / "best.pt"
_MODEL_PATH = Path(os.getenv("MODEL_PATH", str(_DEFAULT_WEIGHTS)))

# Thứ tự nhãn phải khớp đúng dataset huấn luyện dataset_seg_v4
LABELS = ["Answer_paper", "Cheat_Paper", "cellphone"]
# Hai nhãn gian lận: Cheat_Paper và cellphone
CHEAT_LABELS = {"Cheat_Paper", "cellphone"}
# Ngưỡng tin cậy 0,25 và kích thước ảnh infer 512, chỉnh qua biến môi trường.
# 0,25 khớp ngưỡng đã đo kiểm (conf trung bình model ~0,5; 0,5 sẽ lọc mất ~nửa phát hiện đúng)
CONF_THRESHOLD = float(os.getenv("MODEL_CONF", "0.25"))
IMGSZ = int(os.getenv("MODEL_IMGSZ", "512"))

# Màu vẽ khung: bài làm xanh lá, phao đỏ, điện thoại cam
COLORS = {
    "Answer_paper": (0, 255, 0),
    "Cheat_Paper": (0, 0, 255),
    "cellphone": (0, 165, 255),
}

# Nạp model an toàn: thiếu weights thì trả rỗng thay vì crash lúc import
logger.info(f"Loading YOLO26-seg model from: {_MODEL_PATH}")
try:
    _yolo_model = YOLO(str(_MODEL_PATH)) if _MODEL_PATH.exists() else None
    if _yolo_model is None:
        logger.warning(f"Weights not found: {_MODEL_PATH} — inference trả rỗng")
except Exception as exc:
    logger.error(f"Failed to load model: {exc}", exc_info=True)
    _yolo_model = None


def process_frame(
    frame: np.ndarray,
    frame_count: int = 0,
) -> tuple[np.ndarray, list[dict]]:
    """
    Chạy YOLO26-seg trên một frame BGR.
    Điểm logic: ngưỡng tin cậy 0,5 và ảnh infer 512; thiếu model hoặc frame rỗng
    thì trả rỗng; mask nhỏ dưới 100 điểm ảnh thì bỏ để khỏi nhiễu.

    Returns:
        (annotated_frame, detections). Mỗi detection:
        {"bbox": [x1,y1,x2,y2], "mask": [[x,y],...] | None,
         "label": str, "confidence": float, "is_cheat": bool}
    """
    results_data: list[dict] = []
    if _yolo_model is None or frame is None or frame.size == 0:
        return frame, results_data

    try:
        res = _yolo_model(frame, imgsz=IMGSZ, conf=CONF_THRESHOLD, verbose=False)[0]
    except Exception as exc:
        logger.debug(f"Inference failed: {exc}")
        return frame, results_data

    if res.boxes is None or len(res.boxes) == 0:
        return frame, results_data

    names = res.names if hasattr(res, "names") else {i: n for i, n in enumerate(LABELS)}
    masks = res.masks.data.cpu().numpy() if res.masks is not None else None
    h, w = frame.shape[:2]

    for i, box in enumerate(res.boxes):
        try:
            cls_id = int(box.cls[0].item())
            conf = float(box.conf[0].item())
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        except Exception:
            continue

        label = names.get(cls_id, LABELS[cls_id] if cls_id < len(LABELS) else str(cls_id))
        polygon: list[list[int]] | None = None

        # Đổi mask seg thành polygon để vẽ và cho frontend phủ hình
        if masks is not None and i < len(masks):
            try:
                m = (masks[i] > 0.5).astype(np.uint8)
                m = cv2.resize(m, (w, h))
                contours, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if contours:
                    c = max(contours, key=cv2.contourArea)
                    if cv2.contourArea(c) > 100:
                        polygon = c.squeeze(1).tolist()
                        if isinstance(polygon[0], int):
                            polygon = [polygon]
                        pts = np.array(polygon, dtype=np.int32)
                        cv2.polylines(frame, [pts], True, COLORS.get(label, (255, 255, 255)), 2)
            except Exception as exc:
                logger.debug(f"Mask polygon failed: {exc}")

        color = COLORS.get(label, (255, 255, 255))
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            frame, f"{label} {conf:.2f}", (x1, max(0, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2,
        )

        results_data.append({
            "bbox": [x1, y1, x2, y2],
            "mask": polygon,
            "label": label,
            "confidence": round(conf, 4),
            "is_cheat": label in CHEAT_LABELS,
        })

    return frame, results_data


def is_cheat_label(label: str | None) -> bool:
    """Kiểm tra nhãn gian lận (Cheat_Paper hoặc cellphone).
    Điểm logic: nhãn rỗng hoặc Answer_paper thì coi như không gian lận."""
    return (label or "") in CHEAT_LABELS
