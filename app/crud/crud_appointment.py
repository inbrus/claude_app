from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.models import Appointment
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate

class CRUDAppointment(CRUDBase[Appointment, AppointmentCreate, AppointmentUpdate]):
    def get_by_date_range(
        self, 
        db: Session, 
        start_date: datetime,
        end_date: datetime
    ) -> List[Appointment]:
        return db.query(Appointment).filter(
            Appointment.appointment_time >= start_date,
            Appointment.appointment_time <= end_date
        ).all()

    def get_by_client(
        self,
        db: Session,
        client_telegram_id: str
    ) -> List[Appointment]:
        return db.query(Appointment).filter(
            Appointment.client_telegram_id == client_telegram_id
        ).all()

crud_appointment = CRUDAppointment(Appointment)