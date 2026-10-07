"""Bộ công cụ chuẩn hóa và đồng bộ trạng thái hiển thị trên giao diện (Single Source of Truth).

Không hiển thị mã thô từ database (cho_kiem_tra, dang_giam_sat, hoat_dong...).
Tất cả các trang đều sử dụng chung các hàm ánh xạ tại đây để đồng bộ 100% tiếng Việt.
"""

from typing import Tuple, Optional


# =========================================================================
# 1. TRẠNG THÁI SỰ KIỆN KIỂM TRA VI PHẠM (TrangThaiKiemTra)
# =========================================================================
EVENT_STATUS_MAP = {
    "cho_kiem_tra": ("Chờ kiểm tra", "wf-badge warning"),
    "dung": ("Đã xác nhận", "wf-badge success"),
    "sai": ("Bác bỏ", "wf-badge danger"),
    "da_kiem_tra": ("Đã kiểm tra", "wf-badge success"),
    "da_xac_minh": ("Đã xác nhận", "wf-badge success"),
}


def get_event_status_info(status_code: Optional[str]) -> Tuple[str, str]:
    """Trả về (nhãn tiếng Việt, css class badge) của trạng thái sự kiện."""
    if not status_code:
        return ("Chờ kiểm tra", "wf-badge warning")
    key = str(status_code).strip().lower()
    return EVENT_STATUS_MAP.get(key, (key, "wf-badge"))


def get_event_status_label(status_code: Optional[str]) -> str:
    """Trả về chỉ nhãn chữ tiếng Việt chuẩn của trạng thái sự kiện."""
    label, _ = get_event_status_info(status_code)
    return label


def get_event_status_badge(status_code: Optional[str]) -> str:
    """Trả về thẻ HTML badge hoàn chỉnh của trạng thái sự kiện."""
    label, cls = get_event_status_info(status_code)
    return f'<span class="{cls}">{label}</span>'


# =========================================================================
# 2. TRẠNG THÁI CA THI / PHIÊN GIÁM SÁT (TrangThai của PhienGiamSat)
# =========================================================================
def get_session_status_info(status_code: Optional[str] = None, end_time: Optional[str] = None) -> Tuple[str, str]:
    """Xác định trạng thái ca thi dựa trên trường TrangThai hoặc ThoiGianKetThuc."""
    is_ended = bool(end_time) or str(status_code).strip().lower() in ("hoan_thanh", "ket_thuc", "da_ket_thuc", "finished", "done")
    if is_ended:
        return ("Đã kết thúc", "wf-badge success")

    if str(status_code).strip().lower() in ("tam_dung", "paused"):
        return ("Tạm dừng", "wf-badge")

    return ("Đang giám sát", "wf-badge warning")


def get_session_status_label(status_code: Optional[str] = None, end_time: Optional[str] = None) -> str:
    label, _ = get_session_status_info(status_code, end_time)
    return label


def get_session_status_badge(status_code: Optional[str] = None, end_time: Optional[str] = None) -> str:
    label, cls = get_session_status_info(status_code, end_time)
    return f'<span class="{cls}">{label}</span>'


# =========================================================================
# 3. TRẠNG THÁI THIẾT BỊ BIÊN (TrangThai của ThietBiBien)
# =========================================================================
DEVICE_STATUS_MAP = {
    "hoat_dong": ("Trực tuyến", "wf-badge success"),
    "san_sang": ("Trực tuyến", "wf-badge success"),
    "dang_chay": ("Trực tuyến", "wf-badge success"),
    "online": ("Trực tuyến", "wf-badge success"),
    "tam_dung": ("Ngoại tuyến", "wf-badge"),
    "offline": ("Ngoại tuyến", "wf-badge"),
    "ngung_hoat_dong": ("Ngoại tuyến", "wf-badge"),
}


def get_device_status_info(status_code: Optional[str]) -> Tuple[str, str]:
    if not status_code:
        return ("Ngoại tuyến", "wf-badge")
    key = str(status_code).strip().lower()
    return DEVICE_STATUS_MAP.get(key, ("Ngoại tuyến", "wf-badge"))


def get_device_status_label(status_code: Optional[str]) -> str:
    label, _ = get_device_status_info(status_code)
    return label


def get_device_status_badge(status_code: Optional[str]) -> str:
    label, cls = get_device_status_info(status_code)
    return f'<span class="{cls}">{label}</span>'


# =========================================================================
# 4. TRẠNG THÁI NGƯỜI DÙNG & PHÂN QUYỀN (NguoiDung)
# =========================================================================
USER_STATUS_MAP = {
    "hoat_dong": ("Đang hoạt động", "wf-badge success"),
    "active": ("Đang hoạt động", "wf-badge success"),
    "khoa": ("Đã khóa", "wf-badge danger"),
    "tam_khoa": ("Đã khóa", "wf-badge danger"),
    "locked": ("Đã khóa", "wf-badge danger"),
}


def get_user_status_info(status_code: Optional[str]) -> Tuple[str, str]:
    if not status_code:
        return ("Đang hoạt động", "wf-badge success")
    key = str(status_code).strip().lower()
    return USER_STATUS_MAP.get(key, (key, "wf-badge"))


def get_user_status_label(status_code: Optional[str]) -> str:
    label, _ = get_user_status_info(status_code)
    return label


def get_user_status_badge(status_code: Optional[str]) -> str:
    label, cls = get_user_status_info(status_code)
    return f'<span class="{cls}">{label}</span>'


def get_user_role_info(role_code: Optional[str]) -> Tuple[str, str]:
    key = str(role_code).strip().lower() if role_code else "teacher"
    if key == "admin":
        return ("Quản trị viên", "wf-badge danger")
    return ("Cán bộ coi thi", "wf-badge")


def get_user_role_label(role_code: Optional[str]) -> str:
    label, _ = get_user_role_info(role_code)
    return label


def get_user_role_badge(role_code: Optional[str]) -> str:
    label, cls = get_user_role_info(role_code)
    return f'<span class="{cls}">{label}</span>'


# =========================================================================
# 5. HÀNH VI GIAN LẬN / NHÃN AI (LoaiHanhVi, NhanNguoiDung)
# =========================================================================
BEHAVIOR_LABEL_MAP = {
    "cheat_paper": "Tài liệu trái phép",
    "cellphone": "Điện thoại di động",
    "quay_dau": "Quay đầu trao đổi",
    "head_turn": "Quay đầu trao đổi",
    "quay_sau": "Quay người về sau",
    "cui_xuong": "Cúi đầu nhìn xuống bàn",
    "vang_mat": "Vắng mặt khỏi khung hình",
    "nhieu_nguoi": "Nhiều người trong khung hình",
    "answer_paper": "Giấy thi hợp lệ",
    "hop_le": "Giấy thi hợp lệ",
}


def get_friendly_behavior_label(raw_label: Optional[str]) -> str:
    """Chuyển đổi nhãn kỹ thuật tiếng Anh / mã hoá sang tiếng Việt chuẩn."""
    if not raw_label:
        return "Chưa xác minh"
    raw_str = str(raw_label).strip()
    low = raw_str.lower()
    for k, v in BEHAVIOR_LABEL_MAP.items():
        if k in low:
            return v
    return raw_str
