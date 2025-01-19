from sqlalchemy.orm import Session
from app.models.models import Admin
from typing import Optional

class CRUDAdmin:
    async def get_by_telegram_id(self, db: Session, telegram_id: str) -> Optional[Admin]:
        return db.query(Admin).filter(Admin.telegram_id == telegram_id).first()

    async def create(self, db: Session, telegram_id: str, username: str) -> Admin:
        db_admin = Admin(
            telegram_id=telegram_id,
            username=username,
            is_active=True
        )
        db.add(db_admin)
        db.commit()
        db.refresh(db_admin)
        return db_admin

crud_admin = CRUDAdmin()