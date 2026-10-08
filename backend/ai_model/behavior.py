"""Phân loại hành vi đầu từ keypoints COCO-17 (chỉ dùng thân trên).
Luồng chính: keypoints 1 người -> nhin_thang / quay_dau / quay_sau / cui_xuong.

Ngưỡng mặc định chỉnh qua biến môi trường, tune trên footage thật có mặt học sinh.
Video test hiện tại hầu như không thấy đầu nên ngưỡng là provisional.
"""

import os

# Chỉ số keypoints COCO: mũi, mắt, tai, vai
NOSE, L_EYE, R_EYE, L_EAR, R_EAR, L_SHO, R_SHO = 0, 1, 2, 3, 4, 5, 6
FACE_IDXS = (NOSE, L_EYE, R_EYE, L_EAR, R_EAR)

FACE_VIS_MIN = float(os.getenv("BEH_FACE_VIS_MIN", "0.25"))  # conf coi là thấy điểm mặt
SHO_VIS_MIN = float(os.getenv("BEH_SHO_VIS_MIN", "0.35"))   # conf coi là thấy vai
TURN_RATIO = float(os.getenv("BEH_TURN_RATIO", "0.32"))     # mũi lệch / rộng vai (quay đầu)
BEND_RATIO = float(os.getenv("BEH_BEND_RATIO", "0.05"))     # mũi hạ ngang hoặc dưới vai / rộng vai (cúi gục/nhìn gầm)

BEHAVIOR_LABELS = ("nhin_thang", "quay_dau", "quay_sau", "cui_xuong")
CHEAT_BEHAVIORS = {"quay_dau", "quay_sau", "cui_xuong", "vang_mat", "nhieu_nguoi"}


def _v(kpts, i):
    """Trả (x, y, conf) của keypoint i, thiếu thì conf 0."""
    try:
        x, y, c = (float(v) for v in kpts[i])
        return x, y, c
    except Exception:
        return 0.0, 0.0, 0.0


def classify_pose(kpts) -> tuple[str, float]:
    """Phân loại hành vi từ 17 keypoints (x, y, conf).
    Logic chuẩn:
    - Bắt buộc cả 2 vai hợp lệ mới tính theo trục vai (tránh bug 1 vai bị che làm lệch tâm).
    - Quay đầu: mũi lệch tâm vai hoặc bất đối xứng khoảng cách 2 mắt / 1 tai thấy rõ.
    - Cúi xuống: mũi tụt ngang hoặc dưới đường vai (nhìn gầm bàn / cúi gục).
    - Quay sau: thấy rõ cả 2 vai nhưng mất hoàn toàn mặt.
    - Còn lại: nhìn thẳng làm bài bình thường.
    """
    face_c = [_v(kpts, i)[2] for i in FACE_IDXS]
    face_vis = sum(c >= FACE_VIS_MIN for c in face_c)

    lx, ly, lc = _v(kpts, L_SHO)
    rx, ry, rc = _v(kpts, R_SHO)
    both_shoulders = (lc >= SHO_VIS_MIN) and (rc >= SHO_VIS_MIN)

    nx, ny, nc = _v(kpts, NOSE)
    le_x, le_y, le_c = _v(kpts, L_EYE)
    re_x, re_y, re_c = _v(kpts, R_EYE)
    lear_x, lear_y, lear_c = _v(kpts, L_EAR)
    rear_x, rear_y, rear_c = _v(kpts, R_EAR)

    # 1. Quay ra sau: Cả 2 vai thấy rõ và rộng, nhưng mất hoàn toàn các điểm khuôn mặt
    if both_shoulders and face_vis == 0:
        sho_w = abs(rx - lx)
        if sho_w >= 40:  # Đủ gần camera để xác nhận là thân người quay lưng
            conf_val = round(min(0.85, 0.5 + 0.15 * min(lc, rc)), 2)
            return "quay_sau", conf_val

    # 2. Xử lý khi có cả 2 vai (tính toán hình học theo cơ thể chuẩn)
    if both_shoulders:
        sho_mid_x = (lx + rx) / 2.0
        sho_mid_y = (ly + ry) / 2.0
        sho_w = max(abs(rx - lx), 1e-5)

        # Cúi gập đầu / nhìn gầm bàn bất thường: mũi tụt xuống ngang hoặc dưới đường vai
        # (nhìn bài bình thường mũi ở trên vai ny < sho_mid_y)
        if nc >= FACE_VIS_MIN and (ny - sho_mid_y) / sho_w > BEND_RATIO:
            conf_val = round(min(0.95, max(0.6, nc)), 2)
            return "cui_xuong", conf_val

        # Quay đầu theo trục vai: mũi lệch ngang đáng kể so với tâm vai
        if nc >= FACE_VIS_MIN and abs(nx - sho_mid_x) / sho_w > TURN_RATIO:
            conf_val = round(min(0.95, max(0.65, nc)), 2)
            return "quay_dau", conf_val

    # 3. Quay đầu theo đặc trưng bất đối xứng khuôn mặt (hiệu quả cả khi 1 vai hoặc 2 vai bị che)
    # 3a. Bất đối xứng khoảng cách từ mũi tới 2 mắt
    if nc >= FACE_VIS_MIN and le_c >= FACE_VIS_MIN and re_c >= FACE_VIS_MIN:
        d_left = abs(nx - le_x)
        d_right = abs(nx - re_x)
        min_d = min(d_left, d_right)
        max_d = max(d_left, d_right)
        if max_d >= 6.0:
            eye_ratio = max_d / max(min_d, 1e-4)
            if eye_ratio > 2.6:
                conf_val = round(min(0.92, max(0.6, nc)), 2)
                return "quay_dau", conf_val

    # 3b. Chỉ thấy 1 tai rõ và mất hẳn tai còn lại (góc quay đầu nghiêng lớn)
    one_ear = (lear_c >= 0.45 and rear_c < 0.20) or (rear_c >= 0.45 and lear_c < 0.20)
    if one_ear and face_vis <= 3:
        ear_conf = max(lear_c, rear_c)
        return "quay_dau", round(min(0.90, max(0.6, ear_conf)), 2)

    # 4. Mặc định nhìn thẳng làm bài bình thường
    face_conf = (sum(face_c) / len(face_c)) if face_c else 0.0
    return "nhin_thang", round(face_conf, 2)
