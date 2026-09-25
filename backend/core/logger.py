"""Cấu hình ghi log có cấu trúc. Logic: ghi đồng thời ra console và file xoay theo ngày trong backend/logs."""

import logging
from datetime import datetime
from pathlib import Path

_LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
_LOG_DIR.mkdir(exist_ok=True)

_FORMATTER = logging.Formatter(
    fmt="%(asctime)s | %(name)-30s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Tạo hoặc lấy logger có file và console.

    Logic: gọi trùng tên thì trả về cũ, không gắn handler trùng.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(level)

    # File log theo ngày
    log_file = _LOG_DIR / f"{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(_FORMATTER)

    # Đầu ra console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(_FORMATTER)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Lấy logger theo tên. Logic: gọi qua hàm tạo chung bên trên."""
    return setup_logger(name)
