from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api import deps
from app.crud.crud_admin import crud_admin
from app.schemas.admin import Admin, AdminCreate

router = APIRouter()

@router.post("/", response_model=Admin)
def create_admin(
    *,
    db: Session = Depends(deps.get_db),
    admin_in: AdminCreate,
) -> Any:
    """
    Создание нового администратора.
    """
    admin = crud_admin.get_by_telegram_id(db, telegram_id=admin_in.telegram_id)
    if admin:
        raise HTTPException(
            status_code=400,
            detail="Администратор с таким Telegram ID уже существует",
        )
    admin = crud_admin.create(db, obj_in=admin_in)
    return admin

@router.get("/me", response_model=Admin)
def read_admin_me(
    current_admin: Admin = Depends(deps.get_current_admin),
) -> Any:
    """
    Получить текущего администратора.
    """
    return current_admin