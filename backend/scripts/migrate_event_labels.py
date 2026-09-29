"""Nới CHECK LoaiHanhVi cho 3 nhãn hành vi (quay_dau/quay_sau/cui_xuong).
Luồng chính: xóa constraint cũ rồi tạo lại (create_all không tự sửa constraint có sẵn).
Chạy 1 lần sau khi deploy code pose: .venv/bin/python backend/scripts/migrate_event_labels.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from database.database import engine

NEW_VALUES = "('Cheat_Paper', 'cellphone', 'quay_dau', 'quay_sau', 'cui_xuong')"

with engine.begin() as conn:
    conn.execute(text("ALTER TABLE tbl_detected_events DROP CONSTRAINT IF EXISTS ck_event_loai"))
    conn.execute(
        text(
            f'ALTER TABLE tbl_detected_events ADD CONSTRAINT ck_event_loai '
            f'CHECK ("LoaiHanhVi" IN {NEW_VALUES})'
        )
    )
    print(f"ck_event_loai updated: {NEW_VALUES}")
