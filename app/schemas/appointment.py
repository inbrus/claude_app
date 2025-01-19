from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from .service import Service

class AppointmentBase(BaseModel):
    client_telegram_id: str
    client_name: str
    client_phone: str
    service_id: int
    appointment_time: datetime

class AppointmentCreate(AppointmentBase):
    pass

class AppointmentUpdate(BaseModel):
    appointment_time: Optional[datetime] = None
    status: Optional[str] = Field(None, pattern="^(pending|confirmed|cancelled)$")

class Appointment(AppointmentBase):
    id: int
    status: str
    service: Service

    class Config:
        from_attributes = True