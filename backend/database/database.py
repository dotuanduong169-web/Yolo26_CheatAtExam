"""Engine, xưởng session và Base cho DB. Logic: kiểm tra cấu hình rồi tạo engine/session dùng chung."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from core.config import settings

# ── Kiểm tra ──────────────────────────────────────────────
settings.validate()

# ── Engine ──────────────────────────────────────────────────
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
)

# ── Xưởng session ─────────────────────────────────────────
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ── Lớp Base ────────────────────────────────────────
class Base(DeclarativeBase):
    """Lớp cha cho mọi model ORM."""
    pass


# ── Cấp session ──────────────────────────────────────────────
def get_db():
    """Cấp session DB theo request. Logic: mở mỗi request rồi đóng sau khi xong."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()