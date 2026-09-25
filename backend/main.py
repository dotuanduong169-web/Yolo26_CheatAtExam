"""Điểm vào API phát hiện gian lận phòng thi. Logic: khởi tạo FastAPI, gắn CORS/router rồi tạo bảng DB."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from database.database import engine
import models

from api.router import (
    ai_result_router,
    camera_router,
    frame_router,
    history_router,
    statistics_router,
    user_router,
)

# ── Cơ sở dữ liệu ────────────────────────────────────────────────
models.Base.metadata.create_all(bind=engine)

# ── Ứng dụng ─────────────────────────────────────────────
app = FastAPI(
    title="ExamCheat AI Detection API",
    description="API giám sát gian lận phòng thi (YOLO26-seg: Answer_paper/Cheat_Paper/cellphone)",
    version="2.0.0",
)

# ── CORS ────────────────────────────────────────────────────
if settings.is_production:
    allowed_origins = settings.ALLOWED_ORIGINS or ["https://yourdomain.com"]
else:
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    max_age=600,
)

# ── Khai báo router ─────────────────────────────────────────────────
app.include_router(user_router.router)
app.include_router(camera_router.router)
app.include_router(frame_router.router)
app.include_router(statistics_router.router)
app.include_router(history_router.router)
app.include_router(ai_result_router.router)


# ── Kiểm tra sức khỏe ────────────────────────────────────────────
@app.get("/health", tags=["System"])
def health_check():
    """Kiểm tra dịch vụ còn sống."""
    return {"status": "healthy", "environment": settings.ENVIRONMENT}