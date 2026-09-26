"""Tiện ích chốt nhãn hiển thị. Logic: ưu tiên nhãn người sửa trước nhãn AI."""

from models.detected_event import DetectedEvent


def get_final_label(record: DetectedEvent) -> str | None:
    """
    Lấy nhãn cuối cho một sự kiện.

    Logic: có nhãn người sửa thì dùng, không thì lấy nhãn AI.
    """
    return record.NhanNguoiDung if record.NhanNguoiDung is not None else record.NhanAI
