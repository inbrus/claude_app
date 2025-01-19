from typing import List
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.models import Service
from app.schemas.service import ServiceCreate, ServiceUpdate

class CRUDService(CRUDBase[Service, ServiceCreate, ServiceUpdate]):
    def get_active(self, db: Session) -> List[Service]:
        return db.query(Service).filter(Service.is_active == True).all()

crud_service = CRUDService(Service)