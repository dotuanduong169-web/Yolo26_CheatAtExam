"""Cấu hình chung frontend: địa chỉ API FastAPI."""

import os
from dotenv import load_dotenv

load_dotenv()

# Đặt biến môi trường API_BASE_URL khi chạy demo 2 camera qua điện thoại,
# ví dụ: API_BASE_URL=http://192.168.1.123:8000 (điện thoại phải mở được địa chỉ này).
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
