"""Nạp file CSS bọc trong thẻ style để tiêm vào Streamlit."""

from pathlib import Path

# Thư mục gốc frontend (chứa styles/), neo theo vị trí file này để
# chạy đúng dù khởi động Streamlit từ root hay từ frontend/
FRONTEND_ROOT = Path(__file__).resolve().parents[1]


def load_css(file_path: str) -> str:
    """Đọc file CSS và bọc trong thẻ <style>."""
    path = Path(file_path)
    if not path.is_absolute():
        path = FRONTEND_ROOT / file_path
    with open(path, encoding="utf-8") as f:
        return f"<style>{f.read()}</style>"
