"""Nạp file CSS bọc trong thẻ style để tiêm vào Streamlit."""


def load_css(file_path: str) -> str:
    """Đọc file CSS và bọc trong thẻ <style>."""
    with open(file_path, encoding="utf-8") as f:
        return f"<style>{f.read()}</style>"
