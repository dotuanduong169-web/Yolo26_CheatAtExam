"""Bảng người dùng. Logic: một user sở hữu nhiều phiên giám sát, email duy nhất."""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from database.database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False)
    full_name = Column(String, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, default="teacher")

    # Quan hệ
    sessions = relationship("Session", back_populates="user")

    def __repr__(self) -> str:
        """Trả chuỗi nhận diện user theo id và email."""
        return f"<User(id={self.user_id}, email={self.email!r})>"