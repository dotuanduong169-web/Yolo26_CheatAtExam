"""Tạo tài khoản quản trị từ dòng lệnh.
Luồng chính: đọc tên đăng nhập và mật khẩu → kiểm tra trùng → băm mật khẩu rồi lưu DB."""
import sys
import os

# Thêm thư mục backend vào đường dẫn để import được các module trong dự án
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.database import SessionLocal
from models.user import User
from core.security import hash_password
from sqlalchemy.orm import Session

def create_admin(username, password, full_name="System Admin"):
    """Tạo tài khoản quản trị mới.
    Điểm logic: tên đăng nhập đã tồn tại thì bỏ qua; lỗi thì rollback để không ghi dở."""
    db: Session = SessionLocal()
    try:
        # Tên đăng nhập đã tồn tại thì bỏ qua, không tạo trùng
        existing_user = db.query(User).filter(User.TenDangNhap == username).first()
        if existing_user:
            print(f"User with username {username} already exists.")
            return

        # Tạo quản trị mới với mật khẩu đã băm và vai trò admin
        admin_user = User(
            TenDangNhap=username,
            MatKhau=hash_password(password),
            HoVaTen=full_name,
            VaiTro="admin"
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        print(f"Admin user created successfully: {username}")
    except Exception as e:
        db.rollback()
        print(f"Error creating admin user: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python create_admin.py <username> <password> [full_name]")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]
    full_name = sys.argv[3] if len(sys.argv) > 3 else "System Admin"

    create_admin(username, password, full_name)
