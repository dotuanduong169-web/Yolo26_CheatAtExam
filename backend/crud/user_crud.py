"""Quản lý người dùng trong DB.
Logic chính: mật khẩu luôn băm trước khi lưu, tên đăng nhập duy nhất.
"""

from typing import Optional

from sqlalchemy.orm import Session as DBSession

from core.security import hash_password
from models.user import User
from schemas.user import UserCreate


def create_user(db: DBSession, user_data: UserCreate) -> User:
    """Tạo người dùng mới. Băm mật khẩu trước khi lưu, không lưu mật khẩu gốc."""
    db_user = User(
        TenDangNhap=user_data.TenDangNhap,
        MatKhau=hash_password(user_data.MatKhau),
        HoVaTen=user_data.HoVaTen,
        VaiTro=user_data.VaiTro,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user_by_username(db: DBSession, username: str) -> Optional[User]:
    """Tìm người dùng theo tên đăng nhập. Dùng cho đăng nhập và kiểm tra trùng."""
    return db.query(User).filter(User.TenDangNhap == username).first()


def get_user_by_id(db: DBSession, user_id: int) -> Optional[User]:
    """Tìm người dùng theo khóa chính. Dùng cho xác thực và lấy hồ sơ."""
    return db.query(User).filter(User.PK_MaNguoiDung == user_id).first()


def update_user_profile(db: DBSession, user_id: int, ho_va_ten: str) -> Optional[User]:
    """Cập nhật họ tên. Trả về None nếu người dùng không tồn tại."""
    user = db.query(User).filter(User.PK_MaNguoiDung == user_id).first()
    if not user:
        return None

    user.HoVaTen = ho_va_ten
    db.commit()
    db.refresh(user)
    return user


def update_user_password(
    db: DBSession,
    user_id: int,
    hashed_password: str,
) -> bool:
    """Cập nhật mật khẩu (nhận giá trị đã băm sẵn). Trả về False nếu không tồn tại."""
    user = db.query(User).filter(User.PK_MaNguoiDung == user_id).first()
    if not user:
        return False

    user.MatKhau = hashed_password
    db.commit()
    return True


def admin_update_user(
    db: DBSession,
    user_id: int,
    vai_tro: Optional[str] = None,
    trang_thai: Optional[str] = None,
) -> Optional[User]:
    """Admin đổi vai trò/trạng thái. Field None thì giữ nguyên."""
    user = db.query(User).filter(User.PK_MaNguoiDung == user_id).first()
    if not user:
        return None

    if vai_tro is not None:
        user.VaiTro = vai_tro
    if trang_thai is not None:
        user.TrangThai = trang_thai
    db.commit()
    db.refresh(user)
    return user


def list_users(db: DBSession, skip: int = 0, limit: int = 50) -> list[User]:
    """Liệt kê người dùng cho admin."""
    return db.query(User).order_by(User.PK_MaNguoiDung.desc()).offset(skip).limit(limit).all()
