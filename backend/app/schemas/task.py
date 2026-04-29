from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TaskCreate(BaseModel):
    patient_id: str
    description: str
    scheduled_time: str
    task_type: str
    priority: str

class TaskUpdate(BaseModel):
    is_completed: bool

class TaskResponse(TaskCreate):
    id: int
    is_completed: bool
    created_at: datetime

    class Config:
        from_attributes = True
