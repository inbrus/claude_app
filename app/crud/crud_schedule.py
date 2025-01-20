from typing import List, Optional
from datetime import datetime, time
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.models import Schedule, TimeSlot
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate, TimeSlotCreate, TimeSlotUpdate

class CRUDSchedule(CRUDBase[Schedule, ScheduleCreate, ScheduleUpdate]):
    def get_by_admin(self, db: Session, *, admin_id: int) -> List[Schedule]:
        """Получить расписание администратора"""
        return db.query(self.model).filter(Schedule.admin_id == admin_id).all()
    
    def get_by_day(self, db: Session, *, admin_id: int, day_of_week: int) -> Optional[Schedule]:
        """Получить расписание на конкретный день недели"""
        return db.query(self.model).filter(
            Schedule.admin_id == admin_id,
            Schedule.day_of_week == day_of_week
        ).first()

class CRUDTimeSlot(CRUDBase[TimeSlot, TimeSlotCreate, TimeSlotUpdate]):
    def get_by_date_range(
        self, db: Session, *, admin_id: int, start_date: datetime, end_date: datetime
    ) -> List[TimeSlot]:
        """Получить слоты времени в диапазоне дат"""
        return db.query(self.model).filter(
            TimeSlot.admin_id == admin_id,
            TimeSlot.date >= start_date,
            TimeSlot.date <= end_date
        ).all()
    
    def get_available_slots(
        self, db: Session, *, admin_id: int, date: datetime
    ) -> List[TimeSlot]:
        """Получить доступные слоты на конкретную дату"""
        return db.query(self.model).filter(
            TimeSlot.admin_id == admin_id,
            TimeSlot.date == date,
            TimeSlot.is_available == True
        ).all()
    
    def block_slot(
        self, db: Session, *, admin_id: int, date: datetime,
        start_time: time, end_time: time, reason: str
    ) -> TimeSlot:
        """Заблокировать временной слот"""
        slot_in = TimeSlotCreate(
            admin_id=admin_id,
            date=date,
            start_time=start_time,
            end_time=end_time,
            is_available=False,
            reason=reason
        )
        return self.create(db, obj_in=slot_in)

crud_schedule = CRUDSchedule(Schedule)
crud_time_slot = CRUDTimeSlot(TimeSlot)