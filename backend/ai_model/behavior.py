"""Phân loại hành vi đầu từ keypoints COCO-17 (chỉ dùng thân trên).
Luồng chính: keypoints 1 người -> nhin_thang / quay_dau / quay_sau / cui_xuong.

Ngưỡng mặc định chỉnh qua biến môi trường, tune trên footage thật có mặt học sinh.
Video test hiện tại hầu như không thấy đầu nên ngưỡng là provisional.

Chống báo sai khi ánh sáng không đều:
- Chỉ tính tỉ lệ quay đầu khi vai đủ rộng (tránh chia cho vai bị che/cắt khung).
- Ưu tiên trục mũi - trung điểm 2 mắt (ổn định hơn trục vai khi ngồi lệch).
- Không kết luận quay đầu chỉ vì mất một tai/một mắt do bóng đổ/ánh sáng lệch.
"""

import os

# Chỉ số keypoints COCO: mũi, mắt, tai, vai
NOSE, L_EYE, R_EYE, L_EAR, R_EAR, L_SHO, R_SHO = 0, 1, 2, 3, 4, 5, 6
FACE_IDXS = (NOSE, L_EYE, R_EYE, L_EAR, R_EAR)

FACE_VIS_MIN = float(os.getenv("BEH_FACE_VIS_MIN", "0.25"))  # conf coi là thấy điểm mặt
FACE_HIDDEN_MAX = float(os.getenv("BEH_FACE_HIDDEN_MAX", "0.12"))  # dưới mức này mới coi là khuất hẳn
SHO_VIS_MIN = float(os.getenv("BEH_SHO_VIS_MIN", "0.35"))   # conf coi là thấy vai (hỗ trợ webcam góc cận ngực)
TURN_RATIO = float(os.getenv("BEH_TURN_RATIO", "0.32"))     # mũi lệch / rộng vai (quay đầu 30-45 độ)
BEND_RATIO = float(os.getenv("BEH_BEND_RATIO", "0.05"))     # mũi hạ ngang hoặc dưới vai / rộng vai (cúi gục/nhìn gầm)

# Chặn nhiễu hình học khi thí sinh ngồi xa/cắt khung: vai và khoảng cách 2 mắt
# quá nhỏ thì tỉ lệ dao động rất mạnh, không đủ tin cậy để kết luận quay đầu.
MIN_SHOULDER_WIDTH = float(os.getenv("BEH_MIN_SHOULDER_WIDTH", "40"))
MIN_EYE_DIST = float(os.getenv("BEH_MIN_EYE_DIST", "12"))
# Mũi lệch khỏi trung điểm 2 mắt theo phương ngang / khoảng cách 2 mắt.
# Mặt nhìn thẳng thường < 0,20; quay 30-45 độ thường > 0,45.
EYE_YAW_RATIO = float(os.getenv("BEH_EYE_YAW_RATIO", "0.45"))
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

    Thứ tự quyết định:
    - Quay sau: thấy rõ 2 vai đủ rộng nhưng mất hoàn toàn các điểm khuôn mặt.
    - Cúi xuống: mũi tụt ngang hoặc dưới đường vai (nhìn gầm bàn / cúi gục).
    - Quay đầu: mũi lệch khỏi trung điểm 2 mắt, hoặc lệch khỏi tâm vai.
    - Còn lại: nhìn thẳng làm bài bình thường.
    """
    face_c = [_v(kpts, i)[2] for i in FACE_IDXS]

    lx, ly, lc = _v(kpts, L_SHO)
    rx, ry, rc = _v(kpts, R_SHO)
    sho_w = abs(rx - lx)
    both_shoulders = (
        lc >= SHO_VIS_MIN
        and rc >= SHO_VIS_MIN
        and sho_w >= MIN_SHOULDER_WIDTH
    )

    nx, ny, nc = _v(kpts, NOSE)
    le_x, _, le_c = _v(kpts, L_EYE)
    re_x, _, re_c = _v(kpts, R_EYE)

    # 1. Quay ra sau: 2 vai thấy rõ nhưng mất hoàn toàn các điểm khuôn mặt.
    #    Dùng ngưỡng "khuất hẳn" chặt hơn FACE_VIS_MIN: mặt mờ vì thiếu sáng
    #    (conf lửng lơ 0,15-0,24) không bị coi là quay lưng.
    face_hidden = all(c < FACE_HIDDEN_MAX for c in face_c)
    if both_shoulders and face_hidden:
        conf_val = round(min(0.85, 0.5 + 0.15 * min(lc, rc)), 2)
        return "quay_sau", conf_val

    # 2. Cúi gập đầu / nhìn gầm bàn: mũi ngang hoặc dưới đường vai.
    if both_shoulders:
        sho_mid_y = (ly + ry) / 2.0
        if nc >= FACE_VIS_MIN and (ny - sho_mid_y) / sho_w > BEND_RATIO:
            return "cui_xuong", round(min(0.95, max(0.6, nc)), 2)

    # 3. Quay đầu theo trục mắt: ổn định hơn trục vai khi ngồi lệch/ánh sáng lệch.
    #    Mặt nhìn thẳng có mũi gần trung điểm 2 mắt; khi quay, mũi lệch dần sang bên.
    eyes_reliable = (
        nc >= FACE_VIS_MIN
        and le_c >= FACE_VIS_MIN
        and re_c >= FACE_VIS_MIN
        and abs(le_x - re_x) >= MIN_EYE_DIST
    )
    if eyes_reliable:
        eye_dx = abs(le_x - re_x)
        eye_mid_x = (le_x + re_x) / 2.0
        yaw_ratio = abs(nx - eye_mid_x) / eye_dx
        if yaw_ratio > EYE_YAW_RATIO:
            return "quay_dau", round(min(0.92, max(0.6, nc)), 2)
        # Mắt đủ rõ và nói "đang nhìn thẳng": không dùng trục vai nữa, tránh
        # báo oan khi thí sinh ngồi xoay người nhưng đầu vẫn hướng màn hình.
        face_conf = (sum(face_c) / len(face_c)) if face_c else 0.0
        return "nhin_thang", round(face_conf, 2)

    # 4. Quay đầu theo trục vai (chỉ khi mắt không đủ tin cậy).
    if both_shoulders and nc >= FACE_VIS_MIN:
        sho_mid_x = (lx + rx) / 2.0
        if abs(nx - sho_mid_x) / sho_w > TURN_RATIO:
            return "quay_dau", round(min(0.95, max(0.65, nc)), 2)

    # 5. Không dùng "chỉ thấy 1 tai/mắt" làm căn cứ quay đầu: bóng đổ hoặc
    #    ánh sáng lệch bên làm mất keypoint một bên mặt, trước đây gây báo sai.
    #    Trường hợp này bỏ qua (an toàn hơn báo oan); góc quay lớn vẫn được bắt
    #    qua trục mắt/trục vai ở trên khi đủ keypoint.
    face_conf = (sum(face_c) / len(face_c)) if face_c else 0.0
    return "nhin_thang", round(face_conf, 2)
