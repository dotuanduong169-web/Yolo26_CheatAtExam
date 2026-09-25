"""Tạo tài khoản quản trị từ dòng lệnh.
Luồng chính: đọc email và mật khẩu → kiểm tra trùng → băm mật khẩu rồi lưu DB."""
import sys
import os

# Thêm thư mục backend vào đường dẫn để import được các module trong dự án
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.database import SessionLocal
from models.user import User
from core.security import hash_password
from sqlalchemy.orm import Session

def create_admin(email, password, full_name="System Admin"):
    """Tạo tài khoản quản trị mới.
    Điểm logic: email đã tồn tại thì bỏ qua; lỗi thì rollback để không ghi dở."""
    db: Session = SessionLocal()
    try:
        # Email đã tồn tại thì bỏ qua, không tạo trùng
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            print(f"User with email {email} already exists.")
            return

        # Tạo quản trị mới với mật khẩu đã băm và vai trò admin
        admin_user = User(
            email=email,
            password=hash_password(password),
            full_name=full_name,
            role="admin"
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        print(f"Admin user created successfully: {email}")
    except Exception as e:
        db.rollback()
        print(f"Error creating admin user: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python create_admin.py <email> <password> [full_name]")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    full_name = sys.argv[3] if len(sys.argv) > 3 else "System Admin"
    
    create_admin(email, password, full_name)
