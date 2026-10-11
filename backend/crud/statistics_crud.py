"""Quản lý snapshot thống kê theo phiên (đã tinh gọn sang truy vấn trực tiếp từ DetectedEvent)."""

from typing import Any


def create_statistics(db: Any, data: dict, session_id: int) -> None:
    """Không lưu bảng riêng, số liệu được tổng hợp trực tiếp từ DetectedEvent."""
    return None


def get_stats_by_session(db: Any, session_id: int) -> list:
    """Trả về danh sách rỗng vì dữ liệu đã chuyển sang truy vấn trực tiếp."""
    return []

