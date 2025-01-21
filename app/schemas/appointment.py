from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from .service import Service

class AppointmentBase(BaseModel):
    client_telegram_id: str
    client_name: str
    client_phone: Optional[str] = None
    service_id: int
    admin_id: int
    appointment_time: datetime
    status: str = Field(default="pending", pattern="^(pending|confirmed|cancelled)$")

class AppointmentCreate(AppointmentBase):
    pass

class AppointmentUpdate(BaseModel):
    client_name: Optional[str] = None
    client_phone: Optional[str] = None
    service_id: Optional[int] = None
    admin_id: Optional[int] = None
    appointment_time: Optional[datetime] = None
    status: Optional[str] = Field(None, pattern="^(pending|confirmed|cancelled)$")

class Appointment(AppointmentBase):
    id: int
    service: Service

    class Config:
        from_attributes = True

class AppointmentWithDetails(Appointment):
    service_name: str
    service_duration: int
    service_price: float
    admin_username: str