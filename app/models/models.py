from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from .base import BaseModel

class Admin(BaseModel):
    __tablename__ = "admins"
    
    telegram_id = Column(String(100), unique=True, index=True)
    username = Column(String(100))
    is_active = Column(Boolean, default=True)

class Service(BaseModel):
    __tablename__ = "services"
    
    name = Column(String(200), index=True)
    description = Column(String(500), nullable=True)
    price = Column(Float)
    duration = Column(Integer)  # длительность в минутах
    is_active = Column(Boolean, default=True)

class Appointment(BaseModel):
    __tablename__ = "appointments"
    
    client_telegram_id = Column(String(100), index=True)
    client_name = Column(String(200))
    client_phone = Column(String(20))
    service_id = Column(Integer, ForeignKey("services.id"))
    appointment_time = Column(DateTime, index=True)
    status = Column(String(20))  # pending, confirmed, cancelled