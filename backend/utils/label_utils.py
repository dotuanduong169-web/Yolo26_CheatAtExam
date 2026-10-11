"""Tiện ích chốt nhãn hiển thị. Logic: ưu tiên nhãn người sửa trước nhãn AI."""

from models.detected_event import DetectedEvent


def get_final_label(record: DetectedEvent) -> str | None:
    """
    Lấy nhãn cuối cho một sự kiện từ trường LoaiHanhVi duy nhất.
    """
    return getattr(record, "LoaiHanhVi", None)

