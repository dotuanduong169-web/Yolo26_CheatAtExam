"""Script dọn dẹp toàn bộ dữ liệu kiểm thử (test sessions, candidates, events, snapshots, streams).
Giữ lại tài khoản người dùng (admin, giangvien01) và thiết bị biên mặc định.
"""

import sys
import shutil
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from database.database import SessionLocal, engine
from sqlalchemy import text
from core.config import settings

def clear_test_database():
    print("=== BẮT ĐẦU DỌN DẸP DỮ LIỆU KIỂM THỬ ===")
    
    tables_to_clear = [
        "tbl_snapshot_processed",
        "tbl_snapshot",
        "tbl_evidences",
        "tbl_detected_events",
        "tbl_candidate_timeline",
        "tbl_camera_stream",
        "tbl_monitoring_sessions",
        "tbl_thi_sinh",
    ]
    
    with engine.begin() as conn:
        print("1. Truncate các bảng dữ liệu ca thi, thí sinh, sự kiện, bằng chứng...")
        tables_sql = ", ".join(f'"{t}"' for t in tables_to_clear)
        conn.execute(text(f"TRUNCATE TABLE {tables_sql} RESTART IDENTITY CASCADE;"))
        print("   -> Đã xóa sạch dữ liệu và reset identity sequence về 1.")

    with SessionLocal() as db:
        print("\n2. Kiểm tra số lượng bản ghi sau khi dọn dẹp:")
        for t in tables_to_clear:
            cnt = db.execute(text(f'SELECT count(*) FROM "{t}"')).scalar()
            print(f"   - {t}: {cnt} bản ghi")
        
        user_cnt = db.execute(text('SELECT count(*) FROM tbl_user')).scalar()
        users = db.execute(text('SELECT "PK_MaNguoiDung", "TenDangNhap", "VaiTro" FROM tbl_user')).fetchall()
        print(f"\n   - tbl_user (giữ nguyên): {user_cnt} tài khoản -> {users}")
        
        dev_cnt = db.execute(text('SELECT count(*) FROM tbl_edgedevice')).scalar()
        devices = db.execute(text('SELECT "PK_MaThietBi", "TenThietBi" FROM tbl_edgedevice')).fetchall()
        print(f"   - tbl_edgedevice (giữ nguyên): {dev_cnt} thiết bị -> {devices}")

    print("\n3. Dọn dẹp thư mục ảnh test trong images/ ...")
    raw_dir = settings.IMAGE_DIR / "raw"
    processed_dir = settings.IMAGE_DIR / "processed"
    
    for d in [raw_dir, processed_dir]:
        if d.exists():
            for item in d.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                    print(f"   - Đã xóa thư mục ảnh test: {item}")
                elif item.is_file() and not item.name.startswith("."):
                    item.unlink()
                    print(f"   - Đã xóa tệp: {item}")
        else:
            d.mkdir(parents=True, exist_ok=True)
            
    print("\n✅ HOÀN TẤT DỌN DẸP! CSDL ĐÃ SẠCH SẼ, SẴN SÀNG SỬ DỤNG CHO CA THI THẬT.")

if __name__ == "__main__":
    clear_test_database()
