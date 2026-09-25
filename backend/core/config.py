"""Cấu hình tập trung toàn ứng dụng. Logic: đọc biến môi trường kèm mặc định rồi kiểm tra khi khởi động."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Cấu hình ứng dụng đọc từ biến môi trường."""

    # --- Đường dẫn ---
    BASE_DIR: Path = Path(__file__).resolve().parents[1]
    PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
    IMAGE_DIR: Path = PROJECT_ROOT / "images"

    # --- Mô hình AI (giữ nguyên weights YOLO26-seg của dự án) ---
    MODEL_PATH: str = os.getenv("MODEL_PATH", str(BASE_DIR / "ai_model" / "weights" / "best.pt"))
    MODEL_CONF: float = float(os.getenv("MODEL_CONF", "0.5"))
    MODEL_IMGSZ: int = int(os.getenv("MODEL_IMGSZ", "512"))

    # --- Cơ sở dữ liệu ---
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # --- Bảo mật ---
    SECRET_KEY: str = os.getenv("SECRET_KEY", "default-secret-key-change-this")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- Môi trường ---
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1")

    # --- API ---
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))

    # --- CORS ---
    ALLOWED_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    ]

    # --- Giới hạn số lần thử ---
    RATE_LIMIT_MAX_ATTEMPTS: int = 5
    RATE_LIMIT_WINDOW_MINUTES: int = 15

    @property
    def is_production(self) -> bool:
        """Trả True khi chạy môi trường production."""
        return self.ENVIRONMENT == "production"

    def validate(self) -> None:
        """Kiểm tra cấu hình bắt buộc. Logic: thiếu DB hoặc lộ khóa mặc định ở production thì chặn khởi động."""
        if not self.DATABASE_URL:
            raise ValueError("DATABASE_URL must be set in .env file")

        if self.is_production and self.SECRET_KEY == "default-secret-key-change-this":
            raise ValueError("SECRET_KEY must be changed for production")


settings = Settings()
