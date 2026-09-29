"""Phân loại hành vi đầu từ keypoints COCO-17 (chỉ dùng thân trên).
Luồng chính: keypoints 1 người -> nhin_thang / quay_dau / quay_sau / cui_xuong.

Ngưỡng mặc định chỉnh qua biến môi trường, tune trên footage thật có mặt học sinh.
Video test hiện tại hầu như không thấy đầu nên ngưỡng là provisional.
"""

import os

# Chỉ số keypoints COCO: mũi, mắt, tai, vai
NOSE, L_EYE, R_EYE, L_EAR, R_EAR, L_SHO, R_SHO = 0, 1, 2, 3, 4, 5, 6
FACE_IDXS = (NOSE, L_EYE, R_EYE, L_EAR, R_EAR)

FACE_VIS_MIN = float(os.getenv("BEH_FACE_VIS_MIN", "0.25"))  # conf coi là thấy
SHO_VIS_MIN = float(os.getenv("BEH_SHO_VIS_MIN", "0.4"))
TURN_RATIO = float(os.getenv("BEH_TURN_RATIO", "0.35"))  # mũi lệch / rộng vai
BEND_RATIO = float(os.getenv("BEH_BEND_RATIO", "0.9"))  # mũi dưới vai / rộng vai

BEHAVIOR_LABELS = ("nhin_thang", "quay_dau", "quay_sau", "cui_xuong")
CHEAT_BEHAVIORS = {"quay_dau", "quay_sau", "cui_xuong"}


def _v(kpts, i):
    """Trả (x, y, conf) của keypoint i, thiếu thì conf 0."""
    try:
        x, y, c = (float(v) for v in kpts[i])
        return x, y, c
    except Exception:
        return 0.0, 0.0, 0.0


def classify_pose(kpts) -> tuple[str, float]:
    """Phân loại hành vi từ 17 keypoints (x, y, conf).
    Điểm logic: mất mặt + còn vai = quay_sau; mũi tụt sâu dưới vai = cui_xuong;
    mũi lệch ngang khỏi giữa vai = quay_dau; còn lại nhin_thang."""
    face_c = [_v(kpts, i)[2] for i in FACE_IDXS]
    face_vis = sum(c >= FACE_VIS_MIN for c in face_c)

    sho = [_v(kpts, L_SHO), _v(kpts, R_SHO)]
    sho_vis = sum(p[2] >= SHO_VIS_MIN for p in sho)

    if sho_vis == 0:
        return "nhin_thang", 0.0

    # Quay ra sau: mất mặt nhưng còn vai
    if face_vis == 0:
        return "quay_sau", round(min(0.9, 0.5 + 0.1 * sho_vis), 2)

    lx, ly, _ = sho[0]
    rx, ry, _ = sho[1]
    sho_mid_x = (lx + rx) / 2
    sho_mid_y = (ly + ry) / 2
    sho_w = max(abs(rx - lx), 1e-6)

    nx, ny, nc = _v(kpts, NOSE)

    # Cúi xuống bàn: mũi tụt sâu dưới đường vai
    if nc >= FACE_VIS_MIN and (ny - sho_mid_y) / sho_w > BEND_RATIO:
        return "cui_xuong", round(nc, 2)

    # Quay đầu: mũi lệch ngang khỏi giữa vai, hoặc chỉ còn 1 tai
    if nc >= FACE_VIS_MIN and abs(nx - sho_mid_x) / sho_w > TURN_RATIO:
        return "quay_dau", round(nc, 2)
    l_ear_c = _v(kpts, L_EAR)[2]
    r_ear_c = _v(kpts, R_EAR)[2]
    one_ear = (l_ear_c >= 0.4) != (r_ear_c >= 0.4)
    if one_ear and face_vis <= 3:
        return "quay_dau", round(max(l_ear_c, r_ear_c), 2)

    face_conf = sum(face_c) / len(face_c)
    return "nhin_thang", round(face_conf, 2)
