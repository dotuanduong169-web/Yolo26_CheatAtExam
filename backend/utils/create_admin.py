"""Tạo hoặc nâng user thành admin. Logic: có email thì nâng quyền, chưa có thì tạo mới."""

import sys
import os
import argparse

# Thêm thư mục cha để import được module nội bộ
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import SessionLocal
from models.user import User
from core.security import hash_password

def create_or_promote_admin(email, password=None, name=None):
    """Tạo mới hoặc nâng user thành admin. Logic: có thì cập nhật quyền/mật khẩu/tên, chưa có thì bắt buộc đủ mật khẩu và tên."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        
        if user:
            print(f"User {email} found. Promoting to admin...")
            user.role = "admin"
            if password:
                user.password = hash_password(password)
            if name:
                user.full_name = name
            db.commit()
            print(f"Successfully promoted {email} to admin.")
        else:
            if not password or not name:
                print("User not found. To create a new admin, please provide --password and --name.")
                return
            
            print(f"Creating new admin user: {email}...")
            new_user = User(
                email=email,
                password=hash_password(password),
                full_name=name,
                role="admin"
            )
            db.add(new_user)
            db.commit()
            print(f"Successfully created admin user: {email}")
            
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create or promote an admin user.")
    parser.add_argument("--email", required=True, help="Email of the user")
    parser.add_argument("--password", help="Password for the new user (or update existing)")
    parser.add_argument("--name", help="Full name for the new user")
    
    args = parser.parse_args()
    create_or_promote_admin(args.email, args.password, args.name)
