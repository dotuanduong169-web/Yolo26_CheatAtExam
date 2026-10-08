"""Suy luận YOLO26-seg 2 nhãn Cheat_Paper/cellphone cho giám sát thi cử.
Luồng chính: đọc frame → infer một lần → vẽ khung và polygon rồi gắn cờ gian lận."""

import os
import threading
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

from core.config import settings
from core.logger import get_logger
from ai_model.behavior import CHEAT_BEHAVIORS, classify_pose

logger = get_logger(__name__)

# Đường dẫn trọng số, cho phép ghi đè qua biến môi trường MODEL_PATH.
# Ưu tiên bản OpenVINO (nhanh ~2.6x trên CPU), fallback về .pt nếu thiếu.
_AI_MODEL_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _AI_MODEL_DIR.parents[1]
_DEFAULT_WEIGHTS = _AI_MODEL_DIR / "weights" / "best.pt"
_OV_WEIGHTS = _AI_MODEL_DIR / "weights" / "best_openvino_model"


def _resolve_weight(path_str: str | None, default: Path) -> Path:
    """Resolve đường dẫn weights: env tương đối thì tính từ gốc dự án."""
    if not path_str:
        return default
    p = Path(path_str)
    return p if p.is_absolute() else _PROJECT_ROOT / p


_MODEL_PATH = _resolve_weight(
    os.getenv("MODEL_PATH"),
    _OV_WEIGHTS if _OV_WEIGHTS.exists() else _DEFAULT_WEIGHTS,
)

# Thứ tự nhãn phải khớp đúng dataset huấn luyện dataset_kl_rltest_v4 (2 nhãn gian lận)
LABELS = ["Cheat_Paper", "cellphone"]
# Cả hai nhãn model đều là gian lận; frame trắng (không vật) mới coi là sạch
CHEAT_LABELS = {"Cheat_Paper", "cellphone"}
# Ngưỡng tin cậy 0,25 và kích thước ảnh infer 512, chỉnh qua biến môi trường.
# 0,25 khớp ngưỡng đã đo kiểm (conf trung bình model ~0,5; 0,5 sẽ lọc mất ~nửa phát hiện đúng)
CONF_THRESHOLD = float(os.getenv("MODEL_CONF", "0.25"))
IMGSZ = int(os.getenv("MODEL_IMGSZ", "512"))

# Tối ưu đã đo A/B trên videos/test_exam_*.mp4: ByteTrack + giữ box + stride.
# track: cheat_frames +18%, phủ frame +18%; stride 2: tốc độ CPU 3,5→6,8 fps.
# imgsz giữ 512 (đúng cỡ train — 640 làm mất Cheat_Paper đã yếu).
TRACK_ENABLED = os.getenv("MODEL_TRACK", "1") == "1"
TRACK_STRIDE = max(1, int(os.getenv("MODEL_STRIDE", "2")))
TRACK_KEEP = max(1, int(os.getenv("MODEL_KEEP", "5")))
_trackers: dict[str, dict[int, list]] = {}  # ns -> {track_id -> [label, conf, bbox, ttl]
_last_pose_info: dict[str, tuple[int, float]] = {}  # ns -> (số người, conf cao nhất) lần pose gần nhất

# Khóa serialize mọi lệnh infer: model đơn, tracker persist và runtime OV đều
# không an toàn luồng khi worker nhiều phiên gọi đồng thời (CPU-bound nên không mất tốc độ)
_INFER_LOCK = threading.Lock()


def _alive(ns: str = "default") -> dict[int, list]:
    """Bảng track riêng cho từng nguồn (camera phòng / từng thí sinh online)."""
    return _trackers.setdefault(ns, {})

# Model pose (YOLO26n-pose OpenVINO): phát hiện hành vi quay đầu/cúi.
# OV export khóa imgsz 320 — không chỉnh POSE_IMGSZ lên cao hơn.
_POSE_DEFAULT = _AI_MODEL_DIR / "weights" / "yolo26n-pose_openvino_model"
_POSE_PATH = _resolve_weight(os.getenv("POSE_MODEL_PATH"), _POSE_DEFAULT)
POSE_IMGSZ = 320
POSE_CONF = float(os.getenv("POSE_CONF", "0.25"))
POSE_STRIDE = max(1, int(os.getenv("POSE_STRIDE", "3")))
# Giữ box hành vi khi pose miss thoáng qua (cùng vai trò TRACK_KEEP của object)
BEH_KEEP = max(1, int(os.getenv("MODEL_BEH_KEEP", "5")))
BEH_IOU_MATCH = 0.5
_beh_alive: dict[str, list] = {}  # ns -> [[label, conf, bbox, ttl]]


def _bbox_iou(a, b) -> float:
    """IoU hai bbox [x1,y1,x2,y2] để bám box hành vi qua các frame."""
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - ix * iy
    return ix * iy / ua if ua > 0 else 0.0


def _smooth_behavior(ns: str, dets: list[dict]) -> list[dict]:
    """Giữ box hành vi ổn định qua frame miss: khớp IoU cùng nhãn thì tươi TTL,
    box mới thêm vào, box quá hạn xóa. Trả cùng schema kind=behavior."""
    alive = _beh_alive.setdefault(ns, [])
    matched = [False] * len(alive)
    for d in dets:
        bi, bv = -1, BEH_IOU_MATCH
        for i, (lab, _cf, bb, _ttl) in enumerate(alive):
            if matched[i] or lab != d["label"]:
                continue
            v = _bbox_iou(bb, d["bbox"])
            if v >= bv:
                bv, bi = v, i
        if bi >= 0:
            alive[bi] = [d["label"], d["confidence"], d["bbox"], BEH_KEEP]
            matched[bi] = True
        else:
            alive.append([d["label"], d["confidence"], d["bbox"], BEH_KEEP])
            matched.append(True)
    kept = []
    for i, (lab, cf, bb, ttl) in enumerate(alive):
        if not matched[i]:
            ttl -= 1
            alive[i][3] = ttl
            if ttl <= 0:
                continue
        kept.append({
            "bbox": bb, "mask": None, "label": lab,
            "confidence": cf, "is_cheat": True, "kind": "behavior",
        })
    alive[:] = [e for e in alive if e[3] > 0]
    return kept

# Màu vẽ khung: phao đỏ, điện thoại cam, hành vi tím
# (giữ Answer_paper xanh lá để tương thích weights 3 nhãn cũ trong lúc chuyển đổi)
COLORS = {
    "Answer_paper": (0, 255, 0),
    "Cheat_Paper": (0, 0, 255),
    "cellphone": (0, 165, 255),
    "quay_dau": (255, 0, 255),
    "quay_sau": (255, 0, 255),
    "cui_xuong": (255, 0, 255),
}

# Nạp model an toàn: thiếu weights thì trả rỗng thay vì crash lúc import
logger.info(f"Loading YOLO26-seg model from: {_MODEL_PATH}")
try:
    if _MODEL_PATH.exists():
        # Thư mục OpenVINO cần chỉ rõ task, file .pt tự nhận diện
        _yolo_model = (
            YOLO(str(_MODEL_PATH), task="segment")
            if _MODEL_PATH.is_dir()
            else YOLO(str(_MODEL_PATH))
        )
    else:
        _yolo_model = None
        logger.warning(f"Weights not found: {_MODEL_PATH} — inference trả rỗng")
except Exception as exc:
    logger.error(f"Failed to load model: {exc}", exc_info=True)
    _yolo_model = None

# Nạp model pose riêng (thiếu thì chỉ tắt nhánh hành vi, seg vẫn chạy)
logger.info(f"Loading pose model from: {_POSE_PATH}")
try:
    _pose_model = (
        YOLO(str(_POSE_PATH), task="pose") if _POSE_PATH.exists() else None
    )
    if _pose_model is None:
        logger.warning(f"Pose weights not found: {_POSE_PATH} — tắt phát hiện hành vi")
except Exception as exc:
    logger.error(f"Failed to load pose model: {exc}", exc_info=True)
    _pose_model = None


def reset_tracker(ns: str | None = None) -> None:
    """Xóa trạng thái track (gọi khi đổi nguồn video/camera).
    Điểm logic: luôn xóa box giữ lại; chỉ reset predictor với model .pt
    (null predictor làm track() trên OpenVINO trả rỗng vĩnh viễn)."""
    if ns is None:
        _trackers.clear()
        _last_pose_info.clear()
        _beh_alive.clear()
    else:
        _trackers.pop(ns, None)
        _last_pose_info.pop(ns, None)
        _beh_alive.pop(ns, None)
    try:
        # Đặt predictor về None để lần track sau dựng mới hoàn toàn;
        # gán trackers=[] làm track() trả rỗng (đã gặp thực tế).
        if (
            _yolo_model is not None
            and not _MODEL_PATH.is_dir()
            and getattr(_yolo_model, "predictor", None) is not None
        ):
            _yolo_model.predictor = None
    except Exception:
        pass


def _draw_detection(frame, label, conf, bbox, track_id=None) -> None:
    """Vẽ một khung + nhãn lên frame."""
    x1, y1, x2, y2 = bbox
    color = COLORS.get(label, (255, 255, 255))
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    tag = f"{label} {conf:.2f}" + (f" #{track_id}" if track_id is not None else "")
    cv2.putText(
        frame, tag, (x1, max(0, y1 - 8)),
        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2,
    )
def process_frame(
    frame: np.ndarray,
    frame_count: int = 0,
    tracker_ns: str = "default",
) -> tuple[np.ndarray, list[dict]]:
    """
    Chạy YOLO26-seg trên một frame BGR.
    Điểm logic: ngưỡng tin cậy 0,5 và ảnh infer 512; thiếu model hoặc frame rỗng
    thì trả rỗng; mask nhỏ dưới 100 điểm ảnh thì bỏ để khỏi nhiễu.
    tracker_ns tách bảng track theo nguồn (mặc định giữ tương thích gọi cũ).

    Returns:
        (annotated_frame, detections). Mỗi detection:
        {"bbox": [x1,y1,x2,y2], "mask": [[x,y],...] | None,
         "label": str, "confidence": float, "is_cheat": bool}
    """
    results_data: list[dict] = []
    if _yolo_model is None or frame is None or frame.size == 0:
        return frame, results_data

    if TRACK_ENABLED:
        return _process_frame_tracked(frame, frame_count, tracker_ns)

    try:
        with _INFER_LOCK:
            res = _yolo_model(frame, imgsz=IMGSZ, conf=CONF_THRESHOLD, verbose=False)[0]
    except Exception as exc:
        logger.debug(f"Inference failed: {exc}")
        return frame, results_data

    if res.boxes is None or len(res.boxes) == 0:
        return frame, results_data

    names = res.names if hasattr(res, "names") else {i: n for i, n in enumerate(LABELS)}
    # Mask OV model đã là numpy, .pt là torch — xử lý cả hai
    masks = None
    if res.masks is not None:
        md = res.masks.data
        masks = md.cpu().numpy() if hasattr(md, "cpu") else np.asarray(md)
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

        # Đổi mask seg thành polygon để vẽ và cho frontend phủ hình.
        # Contour trên mask gốc nhỏ rồi scale điểm (nhanh hơn resize full-res)
        if masks is not None and i < len(masks):
            try:
                m = (masks[i] > 0.5).astype(np.uint8)
                mh, mw = m.shape
                contours, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if contours:
                    c = max(contours, key=cv2.contourArea)
                    pts = c.squeeze(1).astype(float)
                    pts[:, 0] *= w / mw
                    pts[:, 1] *= h / mh
                    pts = pts.astype(np.int32)
                    if cv2.contourArea(pts) > 100:
                        polygon = pts.tolist()
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
            "kind": "object",
        })

    return frame, results_data


def _run_pose(frame: np.ndarray) -> tuple[list[dict], int, float]:
    """Chạy pose + rule hành vi, trả (detection kind=behavior, số người, conf người cao nhất).
    Điểm logic: bỏ nhin_thang; conf lấy từ rule keypoints; đếm người phục vụ luật vắng mặt/nhiều người."""
    out: list[dict] = []
    try:
        with _INFER_LOCK:
            res = _pose_model(frame, imgsz=POSE_IMGSZ, conf=POSE_CONF, verbose=False)[0]
    except Exception as exc:
        logger.debug(f"Pose inference failed: {exc}")
        return out, 0, 0.0
    if res.boxes is None or res.keypoints is None:
        return out, 0, 0.0
    n_persons = len(res.boxes)
    try:
        person_confs = [float(c) for c in res.boxes.conf.tolist()]
    except Exception:
        person_confs = []
    max_conf = max(person_confs) if person_confs else 0.0
    kpts = res.keypoints.data
    for i, box in enumerate(res.boxes):
        try:
            bbox = list(map(int, box.xyxy[0].tolist()))
        except Exception:
            continue
        if i >= len(kpts):
            continue
        try:
            kp = kpts[i].cpu().numpy() if hasattr(kpts[i], "cpu") else np.asarray(kpts[i])
            label, bconf = classify_pose(kp)
        except Exception:
            continue
        if label not in CHEAT_BEHAVIORS:
            continue
        out.append({
            "bbox": bbox,
            "mask": None,
            "label": label,
            "confidence": round(bconf, 4),
            "is_cheat": True,
            "kind": "behavior",
        })
    return out, n_persons, round(max_conf, 4)


def _process_frame_tracked(
    frame: np.ndarray, frame_count: int = 0, tracker_ns: str = "default"
) -> tuple[np.ndarray, list[dict]]:
    """Bản tối ưu: ByteTrack + infer cách frame + giữ box khi flicker.
    Điểm logic: frame lẻ tái dùng box frame chẵn (giảm nửa infer);
    box mất dấu được giữ TRACK_KEEP frame trước khi xóa;
    pose chạy stride riêng, hành vi gian lận gắn kind=behavior.
    tracker_ns tách bảng track theo nguồn để worker nhiều phiên không lẫn nhau;
    persist=False + lock để an toàn luồng (keep-alive TTL vẫn lo mượt)."""
    alive = _alive(tracker_ns)
    results_data: list[dict] = []
    if frame_count % TRACK_STRIDE == 0:
        try:
            with _INFER_LOCK:
                res = _yolo_model.track(
                    frame, persist=False, tracker="bytetrack.yaml",
                    imgsz=IMGSZ, conf=CONF_THRESHOLD, verbose=False,
                )[0]
        except Exception as exc:
            logger.debug(f"Track inference failed: {exc}")
            return frame, results_data
        names = res.names if hasattr(res, "names") else {
            i: n for i, n in enumerate(LABELS)}
        seen: set[int] = set()
        if res.boxes is not None and len(res.boxes) > 0:
            ids = res.boxes.id
            for idx, box in enumerate(res.boxes):
                try:
                    # ByteTrack đôi khi trả box mà chưa có id (khởi tạo/mất dấu thoáng qua):
                    # gán id tạm âm để detection vẫn đi qua keep-alive thay vì bị vứt
                    track_id = int(ids[idx].item()) if ids is not None else -(idx + 1)
                    cls_id = int(box.cls[0].item())
                    conf = float(box.conf[0].item())
                    bbox = list(map(int, box.xyxy[0].tolist()))
                except Exception:
                    continue
                label = names.get(
                    cls_id, LABELS[cls_id] if cls_id < len(LABELS) else str(cls_id))
                alive[track_id] = [label, conf, bbox, TRACK_KEEP]
                seen.add(track_id)
        for track_id in list(alive):
            if track_id not in seen:
                alive[track_id][3] -= 1
                if alive[track_id][3] <= 0:
                    del alive[track_id]

    for track_id, (label, conf, bbox, _ttl) in alive.items():
        _draw_detection(frame, label, conf, bbox, track_id)
        results_data.append({
            "bbox": bbox,
            "mask": None,
            "label": label,
            "confidence": round(conf, 4),
            "is_cheat": label in CHEAT_LABELS,
            "kind": "object",
            "track_id": track_id,
        })

    if _pose_model is not None and frame_count % POSE_STRIDE == 0:
        pose_dets, n_persons, max_conf = _run_pose(frame)
        _last_pose_info[tracker_ns] = (n_persons, max_conf)
        pose_dets = _smooth_behavior(tracker_ns, pose_dets)
    elif tracker_ns in _beh_alive:
        pose_dets = _smooth_behavior(tracker_ns, [])
    else:
        pose_dets = []
    for b in pose_dets:
        _draw_detection(frame, b["label"], b["confidence"], b["bbox"])
        results_data.append(b)

    return frame, results_data


def is_cheat_label(label: str | None) -> bool:
    """Kiểm tra nhãn gian lận (Cheat_Paper, cellphone hoặc hành vi quay/cúi).
    Điểm logic: model 2 nhãn nên mọi vật detect đều là gian lận;
    nhãn rỗng hay nhãn người sửa Answer_paper/nhin_thang thì coi như không gian lận."""
    return (label or "") in CHEAT_LABELS or (label or "") in CHEAT_BEHAVIORS
