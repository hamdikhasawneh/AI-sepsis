from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String(50), nullable=False)
    description = Column(String(255), nullable=False)
    scheduled_time = Column(String(50), nullable=False)
    task_type = Column(String(50), nullable=False)
    priority = Column(String(50), nullable=False)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Task {self.description} ({self.patient_id})>"
