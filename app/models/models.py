from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .base import BaseModel

class Admin(BaseModel):
    __tablename__ = "admins"
    
    telegram_id = Column(String, unique=True, index=True)
    username = Column(String)
    is_active = Column(Boolean, default=True)

class Service(BaseModel):
    __tablename__ = "services"
    
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    price = Column(Float)
    duration = Column(Integer)  # длительность в минутах
    is_active = Column(Boolean, default=True)

class Appointment(BaseModel):
    __tablename__ = "appointments"
    
    client_telegram_id = Column(String, index=True)
    client_name = Column(String)
    client_phone = Column(String)
    service_id = Column(Integer, ForeignKey("services.id"))
    appointment_time = Column(DateTime, index=True)
    status = Column(String)  # pending, confirmed, cancelled
    
    service = relationship("Service")