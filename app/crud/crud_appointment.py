from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload
from app.crud.base import CRUDBase
from app.models.models import Appointment, Service, Admin, Schedule, TimeSlot
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate

class CRUDAppointment(CRUDBase[Appointment, AppointmentCreate, AppointmentUpdate]):
    def get_by_date_range(
        self, 
        db: Session, 
        start_date: datetime,
        end_date: datetime,
        admin_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[Appointment]:
        query = db.query(Appointment).options(
            joinedload(Appointment.service)
        ).filter(
            Appointment.appointment_time >= start_date,
            Appointment.appointment_time <= end_date
        )
        
        if admin_id is not None:
            query = query.filter(Appointment.admin_id == admin_id)
        
        if status:
            query = query.filter(Appointment.status == status)
        
        return query.order_by(Appointment.appointment_time).all()

    def get_by_client(
        self,
        db: Session,
        client_telegram_id: str,
        include_past: bool = False
    ) -> List[Appointment]:
        query = db.query(Appointment).options(
            joinedload(Appointment.service)
        ).filter(
            Appointment.client_telegram_id == client_telegram_id
        )
        
        if not include_past:
            query = query.filter(
                Appointment.appointment_time >= datetime.now(),
                Appointment.status != "cancelled"
            )
        
        return query.order_by(Appointment.appointment_time).all()
    
    def get_available_slots(
        self,
        db: Session,
        admin_id: int,
        date: datetime,
        service_duration: int
    ) -> List[datetime]:
        """Получить доступные слоты для записи на конкретную дату"""
        # Получаем расписание на этот день недели
        day_schedule = db.query(Schedule).filter(
            Schedule.admin_id == admin_id,
            Schedule.day_of_week == date.weekday(),
            Schedule.is_working == True
        ).first()
        
        if not day_schedule:
            return []
        
        # Получаем все записи на этот день
        day_start = datetime.combine(date.date(), day_schedule.start_time)
        day_end = datetime.combine(date.date(), day_schedule.end_time)
        
        appointments = db.query(Appointment).filter(
            Appointment.admin_id == admin_id,
            Appointment.appointment_time >= day_start,
            Appointment.appointment_time <= day_end,
            Appointment.status != "cancelled"
        ).all()
        
        # Получаем заблокированные слоты
        blocked_slots = db.query(TimeSlot).filter(
            TimeSlot.admin_id == admin_id,
            TimeSlot.date == date.date(),
            TimeSlot.is_available == False
        ).all()
        
        # Создаем список всех возможных слотов
        slots = []
        current_time = day_start
        slot_duration = timedelta(minutes=service_duration)
        
        while current_time + slot_duration <= day_end:
            # Проверяем, не попадает ли слот на перерыв
            if day_schedule.break_start and day_schedule.break_end:
                break_start = datetime.combine(date.date(), day_schedule.break_start)
                break_end = datetime.combine(date.date(), day_schedule.break_end)
                if current_time < break_end and current_time + slot_duration > break_start:
                    current_time = break_end
                    continue
            
            # Проверяем, не занят ли слот другими записями
            slot_is_free = True
            for appointment in appointments:
                appointment_end = appointment.appointment_time + timedelta(
                    minutes=appointment.service.duration
                )
                if (current_time < appointment_end and 
                    current_time + slot_duration > appointment.appointment_time):
                    slot_is_free = False
                    break
            
            # Проверяем, не попадает ли слот на заблокированное время
            for blocked_slot in blocked_slots:
                slot_start = datetime.combine(date.date(), blocked_slot.start_time)
                slot_end = datetime.combine(date.date(), blocked_slot.end_time)
                if current_time < slot_end and current_time + slot_duration > slot_start:
                    slot_is_free = False
                    break
            
            if slot_is_free:
                slots.append(current_time)
            
            current_time += timedelta(minutes=30)  # Шаг в 30 минут
        
        return slots
    
    def create_with_validation(
        self,
        db: Session,
        *,
        obj_in: AppointmentCreate
    ) -> Appointment:
        """Создание записи с проверкой доступности времени"""
        # Проверяем существование услуги
        service = db.query(Service).filter(
            Service.id == obj_in.service_id,
            Service.is_active == True
        ).first()
        if not service:
            raise ValueError("Услуга не найдена или неактивна")
        
        # Проверяем доступность времени
        available_slots = self.get_available_slots(
            db,
            obj_in.admin_id,
            obj_in.appointment_time,
            service.duration
        )
        
        if obj_in.appointment_time not in available_slots:
            raise ValueError("Выбранное время недоступно для записи")
        
        return super().create(db, obj_in=obj_in)
    
    def update_status(
        self,
        db: Session,
        *,
        appointment_id: int,
        new_status: str
    ) -> Optional[Appointment]:
        """Обновление статуса записи"""
        appointment = self.get(db, id=appointment_id)
        if not appointment:
            return None
        
        appointment_in = AppointmentUpdate(status=new_status)
        return self.update(db, db_obj=appointment, obj_in=appointment_in)

crud_appointment = CRUDAppointment(Appointment)