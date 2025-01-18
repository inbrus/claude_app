from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.api import deps
from app.crud.crud_appointment import crud_appointment
from app.models.models import Admin
from app.schemas.appointment import Appointment, AppointmentCreate, AppointmentUpdate

router = APIRouter()

@router.get("/", response_model=List[Appointment])
def read_appointments(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_admin: Admin = Depends(deps.get_current_admin),
) -> Any:
    """
    Получить список всех записей.
    """
    appointments = crud_appointment.get_multi(db, skip=skip, limit=limit)
    return appointments

@router.post("/", response_model=Appointment)
def create_appointment(
    *,
    db: Session = Depends(deps.get_db),
    appointment_in: AppointmentCreate,
) -> Any:
    """
    Создать новую запись.
    """
    # Проверка на доступность времени
    start_time = appointment_in.appointment_time
    end_time = start_time + timedelta(minutes=30)  # Предполагаемая длительность
    existing = crud_appointment.get_by_date_range(db, start_time, end_time)
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Выбранное время уже занято",
        )
    
    appointment = crud_appointment.create(db, obj_in=appointment_in)
    return appointment

@router.put("/{appointment_id}", response_model=Appointment)
def update_appointment(
    *,
    db: Session = Depends(deps.get_db),
    appointment_id: int,
    appointment_in: AppointmentUpdate,
    current_admin: Admin = Depends(deps.get_current_admin),
) -> Any:
    """
    Обновить запись.
    """
    appointment = crud_appointment.get(db, id=appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    
    if appointment_in.appointment_time:
        # Проверка на доступность нового времени
        start_time = appointment_in.appointment_time
        end_time = start_time + timedelta(minutes=30)
        existing = crud_appointment.get_by_date_range(db, start_time, end_time)
        if existing and existing.id != appointment_id:
            raise HTTPException(
                status_code=400,
                detail="Выбранное время уже занято",
            )
    
    appointment = crud_appointment.update(db, db_obj=appointment, obj_in=appointment_in)
    return appointment

@router.delete("/{appointment_id}", response_model=Appointment)
def delete_appointment(
    *,
    db: Session = Depends(deps.get_db),
    appointment_id: int,
    current_admin: Admin = Depends(deps.get_current_admin),
) -> Any:
    """
    Удалить запись.
    """
    appointment = crud_appointment.get(db, id=appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    appointment = crud_appointment.remove(db, id=appointment_id)
    return appointment