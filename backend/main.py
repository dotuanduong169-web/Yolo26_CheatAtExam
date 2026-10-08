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
    candidate_router,
    device_router,
    event_router,
    history_router,
    ingest_router,
    statistics_router,
    user_router,
)

# ── Cơ sở dữ liệu ────────────────────────────────────────────────
models.Base.metadata.create_all(bind=engine)

def ensure_online_exam_migrations():
    """Tự động bổ sung các cột mới và relax constraint cần thiết cho thi online nếu chưa có."""
    from sqlalchemy import text
    try:
        with engine.begin() as conn:
            # 1. Cột FK_MaThiSinh trên tbl_monitoring_sessions
            conn.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'tbl_monitoring_sessions' AND column_name = 'FK_MaThiSinh'
                    ) THEN
                        ALTER TABLE tbl_monitoring_sessions
                            ADD COLUMN "FK_MaThiSinh" BIGINT REFERENCES tbl_thi_sinh("PK_MaThiSinh") ON DELETE SET NULL;
                    END IF;
                END $$;
            """))
            # 2. Cho phép FK_MaThietBi nullable trên phiên online (không gắn camera vật lý)
            conn.execute(text("""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'tbl_monitoring_sessions' AND column_name = 'FK_MaThietBi'
                            AND is_nullable = 'NO'
                    ) THEN
                        ALTER TABLE tbl_monitoring_sessions ALTER COLUMN "FK_MaThietBi" DROP NOT NULL;
                    END IF;
                END $$;
            """))
            # 3. Mở rộng ràng buộc các loại hành vi thi online
            conn.execute(text("ALTER TABLE tbl_detected_events DROP CONSTRAINT IF EXISTS ck_event_loai"))
            conn.execute(text("""
                ALTER TABLE tbl_detected_events ADD CONSTRAINT ck_event_loai
                CHECK ("LoaiHanhVi" IN ('Cheat_Paper', 'cellphone', 'quay_dau', 'quay_sau', 'cui_xuong', 'vang_mat', 'nhieu_nguoi'))
            """))
    except Exception as exc:
        print(f"[WARN] Không thể tự động chạy migration online exam: {exc}")

try:
    ensure_online_exam_migrations()
except Exception as exc:
    print(f"[WARN] Lỗi khi gọi ensure_online_exam_migrations: {exc}")

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
    description="API giám sát gian lận phòng thi (YOLO26-seg: Cheat_Paper/cellphone)",
    version="2.0.0",
)

# ── CORS ────────────────────────────────────────────────────
if settings.is_production:
    allowed_origins = settings.ALLOWED_ORIGINS or ["https://yourdomain.com"]
else:
    allowed_origins = settings.ALLOWED_ORIGINS or [
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost:8502",
        "http://127.0.0.1:8502",
    ]

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
app.include_router(candidate_router.router)
app.include_router(device_router.router)
app.include_router(ingest_router.router)
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


# ── Trang thi online cho thí sinh ────────────────────────────
@app.get("/exam", include_in_schema=False)
def exam_page():
    """Trả trang HTML thí sinh: nhập SBD, mở camera, nộp frame nền."""
    return FileResponse(Path(__file__).resolve().parent / "static" / "exam.html")