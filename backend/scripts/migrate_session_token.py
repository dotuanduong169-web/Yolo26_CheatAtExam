"""Thêm cột TokenThamGia cho phiên con thi online.
Luồng chính: ALTER ADD COLUMN IF NOT EXISTS (create_all không tự thêm cột vào bảng có sẵn).
Token lưu DB để sống sót qua restart và nhiều tiến trình uvicorn.
Chạy 1 lần sau khi deploy: .venv/bin/python backend/scripts/migrate_session_token.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from database.database import engine

with engine.begin() as conn:
    conn.execute(text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'tbl_monitoring_sessions' AND column_name = 'TokenThamGia'
            ) THEN
                ALTER TABLE tbl_monitoring_sessions ADD COLUMN "TokenThamGia" VARCHAR(255);
            END IF;
        END $$;
    """))
    conn.execute(text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes WHERE indexname = 'ix_session_token'
            ) THEN
                CREATE INDEX ix_session_token ON tbl_monitoring_sessions ("TokenThamGia");
            END IF;
        END $$;
    """))
    print("TokenThamGia ensured")
