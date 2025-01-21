from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Time
from sqlalchemy.sql import func
from .base import BaseModel
from datetime import time

class Admin(BaseModel):
    __tablename__ = "admins"
    
    telegram_id = Column(String(100), unique=True, index=True)
    username = Column(String(100))
    is_active = Column(Boolean, default=True)

class ServiceCategory(BaseModel):
    __tablename__ = "service_categories"
    
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    order = Column(Integer, default=0)  # для сортировки
    is_active = Column(Boolean, default=True)

class Service(BaseModel):
    __tablename__ = "services"
    
    name = Column(String(200), index=True)
    description = Column(String(500), nullable=True)
    price = Column(Float)
    duration = Column(Integer)  # длительность в минутах
    category_id = Column(Integer, ForeignKey("service_categories.id"), nullable=True)
    order = Column(Integer, default=0)  # для сортировки внутри категории
    is_active = Column(Boolean, default=True)

class Schedule(BaseModel):
    __tablename__ = "schedules"
    
    admin_id = Column(Integer, ForeignKey("admins.id"))
    day_of_week = Column(Integer)  # 0-6 (пн-вс)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    is_working = Column(Boolean, default=True)  # рабочий или выходной день
    break_start = Column(Time, nullable=True)  # начало перерыва
    break_end = Column(Time, nullable=True)    # конец перерыва

class TimeSlot(BaseModel):
    __tablename__ = "time_slots"
    
    admin_id = Column(Integer, ForeignKey("admins.id"))
    date = Column(DateTime, index=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    is_available = Column(Boolean, default=True)
    reason = Column(String(200), nullable=True)  # причина блокировки слота

class Appointment(BaseModel):
    __tablename__ = "appointments"
    
    client_telegram_id = Column(String(100), index=True)
    client_name = Column(String(200))
    client_phone = Column(String(20))
    service_id = Column(Integer, ForeignKey("services.id"))
    admin_id = Column(Integer, ForeignKey("admins.id"))
    appointment_time = Column(DateTime, index=True)
    status = Column(String(20))  # pending, confirmed, cancelled