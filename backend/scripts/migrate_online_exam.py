"""Migrate thi online: bảng tbl_thi_sinh + FK_MaThiSinh + device nullable + CHECK LoaiHanhVi mới.
Luồng chính: create_all tạo bảng mới; ALTER bổ sung cột/constraint mà create_all không tự làm.
Chạy 1 lần sau khi deploy: .venv/bin/python backend/scripts/migrate_online_exam.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from database.database import Base, engine

import models  # noqa: F401 — đăng ký đủ model cho create_all

NEW_BEHAVIORS = "('Cheat_Paper', 'cellphone', 'quay_dau', 'quay_sau', 'cui_xuong', 'vang_mat', 'nhieu_nguoi')"

# 1. Bảng mới (tbl_thi_sinh) — create_all tự tạo nếu chưa có
Base.metadata.create_all(bind=engine, tables=[Base.metadata.tables["tbl_thi_sinh"]])
print("tbl_thi_sinh ensured")

with engine.begin() as conn:
    # 2. FK_MaThiSinh nullable trên phiên (phiên con của thí sinh)
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
    print("FK_MaThiSinh ensured")

    # 3. Phiên online không gắn thiết bị biên -> FK_MaThietBi nullable
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
    print("FK_MaThietBi nullable ensured")

    # 4. Nới CHECK LoaiHanhVi thêm vang_mat/nhieu_nguoi
    conn.execute(text("ALTER TABLE tbl_detected_events DROP CONSTRAINT IF EXISTS ck_event_loai"))
    conn.execute(
        text(
            f'ALTER TABLE tbl_detected_events ADD CONSTRAINT ck_event_loai '
            f'CHECK ("LoaiHanhVi" IN {NEW_BEHAVIORS})'
        )
    )
    print(f"ck_event_loai updated: {NEW_BEHAVIORS}")

print("Migrate online exam xong")
