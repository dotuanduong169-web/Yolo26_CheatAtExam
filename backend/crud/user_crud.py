"""Quản lý người dùng trong DB.
Logic chính: mật khẩu luôn băm trước khi lưu, cập nhật xong commit rồi refresh.
"""

from typing import Optional

from sqlalchemy.orm import Session as DBSession

from core.security import hash_password
from models.user import User
from schemas.user import UserCreate


def create_user(db: DBSession, user_data: UserCreate) -> User:
    """Tạo người dùng mới. Băm mật khẩu trước khi lưu, không lưu mật khẩu gốc."""
    db_user = User(
        full_name=user_data.full_name,
        email=user_data.email,
        password=hash_password(user_data.password),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user_by_email(db: DBSession, email: str) -> Optional[User]:
    """Tìm người dùng theo email. Dùng cho đăng nhập và kiểm tra trùng email."""
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: DBSession, user_id: int) -> Optional[User]:
    """Tìm người dùng theo khóa chính. Dùng cho xác thực và lấy hồ sơ."""
    return db.query(User).filter(User.user_id == user_id).first()


def update_user_profile(
    db: DBSession,
    user_id: int,
    full_name: str,
    email: str,
) -> Optional[User]:
    """Cập nhật tên hiển thị và email. Trả về None nếu người dùng không tồn tại."""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return None

    user.full_name = full_name
    user.email = email
    db.commit()
    db.refresh(user)
    return user


def update_user_password(
    db: DBSession,
    user_id: int,
    hashed_password: str,
) -> bool:
    """Cập nhật mật khẩu (nhận giá trị đã băm sẵn). Trả về False nếu không tồn tại."""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return False

    user.password = hashed_password
    db.commit()
    return True
