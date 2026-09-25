"""Tiện ích chốt nhãn hiển thị. Logic: ưu tiên nhãn người sửa trước nhãn AI."""

from models.ai_result import AIResult


def get_final_label(record: AIResult) -> str | None:
    """
    Lấy nhãn cuối cho một kết quả.

    Logic: có nhãn người sửa thì dùng, không thì lấy nhãn AI.
    """
    return record.user_label if record.user_label is not None else record.ai_label