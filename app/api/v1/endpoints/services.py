from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api import deps
from app.crud.crud_service import crud_service
from app.models.models import Admin
from app.schemas.service import Service, ServiceCreate, ServiceUpdate

router = APIRouter()

@router.get("/", response_model=List[Service])
def read_services(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Получить список всех услуг.
    """
    services = crud_service.get_multi(db, skip=skip, limit=limit)
    return services

@router.post("/", response_model=Service)
def create_service(
    *,
    db: Session = Depends(deps.get_db),
    service_in: ServiceCreate,
    current_admin: Admin = Depends(deps.get_current_admin),
) -> Any:
    """
    Создать новую услугу.
    """
    service = crud_service.create(db, obj_in=service_in)
    return service

@router.put("/{service_id}", response_model=Service)
def update_service(
    *,
    db: Session = Depends(deps.get_db),
    service_id: int,
    service_in: ServiceUpdate,
    current_admin: Admin = Depends(deps.get_current_admin),
) -> Any:
    """
    Обновить услугу.
    """
    service = crud_service.get(db, id=service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Услуга не найдена")
    service = crud_service.update(db, db_obj=service, obj_in=service_in)
    return service

@router.delete("/{service_id}", response_model=Service)
def delete_service(
    *,
    db: Session = Depends(deps.get_db),
    service_id: int,
    current_admin: Admin = Depends(deps.get_current_admin),
) -> Any:
    """
    Удалить услугу.
    """
    service = crud_service.get(db, id=service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Услуга не найдена")
    service = crud_service.remove(db, id=service_id)
    return service