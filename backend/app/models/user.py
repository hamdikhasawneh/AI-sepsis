from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(120), nullable=False)
    role = Column(String(20), nullable=False)  # admin, doctor, nurse
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    assigned_patients = relationship(
        "Patient", back_populates="assigned_doctor", foreign_keys="Patient.assigned_doctor_id"
    )
    created_patients = relationship(
        "Patient", back_populates="created_by_user", foreign_keys="Patient.created_by_user_id"
    )

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"
