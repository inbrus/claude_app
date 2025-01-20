from pydantic import BaseModel, Field
from typing import Optional
from datetime import time, datetime

class ScheduleBase(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    start_time: time
    end_time: time
    is_working: bool = True
    break_start: Optional[time] = None
    break_end: Optional[time] = None

class ScheduleCreate(ScheduleBase):
    admin_id: int

class ScheduleUpdate(BaseModel):
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    is_working: Optional[bool] = None
    break_start: Optional[time] = None
    break_end: Optional[time] = None

class Schedule(ScheduleBase):
    id: int
    admin_id: int

    class Config:
        from_attributes = True

class TimeSlotBase(BaseModel):
    date: datetime
    start_time: time
    end_time: time
    is_available: bool = True
    reason: Optional[str] = None

class TimeSlotCreate(TimeSlotBase):
    admin_id: int

class TimeSlotUpdate(BaseModel):
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    is_available: Optional[bool] = None
    reason: Optional[str] = None

class TimeSlot(TimeSlotBase):
    id: int
    admin_id: int

    class Config:
        from_attributes = True