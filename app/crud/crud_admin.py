from typing import Optional
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.models import Admin
from app.schemas.admin import AdminCreate, Admin as AdminSchema

class CRUDAdmin(CRUDBase[Admin, AdminCreate, AdminSchema]):
    def get_by_telegram_id(self, db: Session, telegram_id: str) -> Optional[Admin]:
        return db.query(Admin).filter(Admin.telegram_id == telegram_id).first()

crud_admin = CRUDAdmin(Admin)