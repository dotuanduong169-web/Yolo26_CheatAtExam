"""Kết quả nhận diện AI trên frame. Logic: gắn với một frame, ưu tiên nhãn người sửa trước nhãn AI."""

from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database.database import Base


class AIResult(Base):
    __tablename__ = "ai_results"

    result_id = Column(Integer, primary_key=True, index=True)
    temporary_student_id = Column(String(100))
    face_bbox = Column(String)
    ai_label = Column(String(100), nullable=False)
    user_label = Column(String(100), nullable=True)
    confidence = Column(Float, nullable=False)
    frame_id = Column(Integer, ForeignKey("frames.frame_id", ondelete="CASCADE"))

    # Quan hệ
    frame = relationship("Frame", back_populates="ai_results")

    def __repr__(self) -> str:
        """Trả chuỗi nhận diện kết quả theo id và nhãn AI."""
        return f"<AIResult(id={self.result_id}, label={self.ai_label!r})>"