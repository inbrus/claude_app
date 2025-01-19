from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.crud.crud_admin import crud_admin
from app.models.models import Admin

def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

def get_current_admin(
    db: Session = Depends(get_db),
    telegram_id: str = None
) -> Admin:
    if not telegram_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    admin = crud_admin.get_by_telegram_id(db, telegram_id=telegram_id)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin not found",
        )
    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive admin",
        )
    return admin