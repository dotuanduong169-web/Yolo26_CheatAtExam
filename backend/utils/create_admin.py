"""Tạo hoặc nâng user thành admin. Logic: có tên đăng nhập thì nâng quyền, chưa có thì tạo mới."""

import sys
import os
import argparse

# Thêm thư mục cha để import được module nội bộ
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import SessionLocal
from models.user import User
from core.security import hash_password

def create_or_promote_admin(username, password=None, name=None):
    """Tạo mới hoặc nâng user thành admin. Logic: có thì cập nhật quyền/mật khẩu/tên, chưa có thì bắt buộc đủ mật khẩu và tên."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.TenDangNhap == username).first()

        if user:
            print(f"User {username} found. Promoting to admin...")
            user.VaiTro = "admin"
            if password:
                user.MatKhau = hash_password(password)
            if name:
                user.HoVaTen = name
            db.commit()
            print(f"Successfully promoted {username} to admin.")
        else:
            if not password or not name:
                print("User not found. To create a new admin, please provide --password and --name.")
                return

            print(f"Creating new admin user: {username}...")
            new_user = User(
                TenDangNhap=username,
                MatKhau=hash_password(password),
                HoVaTen=name,
                VaiTro="admin"
            )
            db.add(new_user)
            db.commit()
            print(f"Successfully created admin user: {username}")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create or promote an admin user.")
    parser.add_argument("--username", required=True, help="TenDangNhap of the user")
    parser.add_argument("--password", help="Password for the new user (or update existing)")
    parser.add_argument("--name", help="HoVaTen for the new user")

    args = parser.parse_args()
    create_or_promote_admin(args.username, args.password, args.name)
