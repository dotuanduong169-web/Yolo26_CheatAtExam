"""Nạp CSS cho các trang Streamlit.
Luồng chính: đọc file CSS -> bọc trong thẻ <style> để nhúng vào trang."""


def load_css(file_path: str) -> str:
    """Đọc file CSS và bọc trong thẻ <style> để nhúng vào Streamlit."""
    with open(file_path, encoding="utf-8") as f:
        return f"<style>{f.read()}</style>"