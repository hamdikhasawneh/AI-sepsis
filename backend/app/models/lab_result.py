from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base

class LabResult(Base):
    __tablename__ = "lab_results"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String(50), nullable=False)
    test_name = Column(String(100), nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)
    reference_range = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<LabResult {self.test_name} = {self.value} {self.unit}>"
