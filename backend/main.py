"""Điểm vào API phát hiện gian lận phòng thi. Logic: khởi tạo FastAPI, gắn CORS/router rồi tạo bảng DB."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path

from core.config import settings
from database.database import engine
import models

from api.router import (
    camera_router,
    device_router,
    event_router,
    history_router,
    statistics_router,
    user_router,
)

# ── Cơ sở dữ liệu ────────────────────────────────────────────────
models.Base.metadata.create_all(bind=engine)

def init_default_admin():
    """Tự động tạo tài khoản admin mặc định nếu chưa tồn tại."""
    from database.database import SessionLocal
    from models.user import User
    from core.security import hash_password
    with SessionLocal() as db:
        admin_exists = db.query(User).filter(
            User.TenDangNhap == "admin"
        ).first()
        if not admin_exists:
            admin_user = User(
                TenDangNhap="admin",
                MatKhau=hash_password("Admin123"),
                HoVaTen="Quản trị viên Hệ thống",
                VaiTro="admin",
                TrangThai="hoat_dong",
            )
            try:
                db.add(admin_user)
                db.commit()
            except Exception:
                db.rollback()
                raise
            print("[INFO] Đã tự động khởi tạo tài khoản admin mặc định: admin / Admin123")

try:
    init_default_admin()
except Exception as exc:
    print(f"[WARN] Không thể kiểm tra/khởi tạo admin: {exc}")

try:
    from service.camera_service import cleanup_orphan_sessions
    cleared = cleanup_orphan_sessions()
    if cleared:
        print(f"[INFO] Đã dọn dẹp {cleared} phiên mồ côi bị treo")
except Exception as exc:
    print(f"[WARN] Không thể dọn dẹp phiên mồ côi: {exc}")

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
app.include_router(device_router.router)
app.include_router(event_router.router)
app.include_router(statistics_router.router)
app.include_router(history_router.router)


# ── Kiểm tra sức khỏe ────────────────────────────────────────────
@app.get("/health", tags=["System"])
def health_check():
    """Kiểm tra dịch vụ còn sống."""
    return {"status": "healthy", "environment": settings.ENVIRONMENT}


# ── Trang test camera đơn giản ─────────────────────────────────
@app.get("/camera-test", include_in_schema=False)
def camera_test_page():
    """Trả trang HTML test camera máy + AI nhận diện."""
    return FileResponse(Path(__file__).resolve().parent / "static" / "camera_test.html")