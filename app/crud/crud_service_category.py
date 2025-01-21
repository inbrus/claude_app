from typing import List, Optional
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.models import ServiceCategory
from app.schemas.service import ServiceCategoryCreate, ServiceCategoryUpdate

class CRUDServiceCategory(CRUDBase[ServiceCategory, ServiceCategoryCreate, ServiceCategoryUpdate]):
    def get_active(self, db: Session) -> List[ServiceCategory]:
        """Получить все активные категории"""
        return (
            db.query(self.model)
            .filter(ServiceCategory.is_active == True)
            .order_by(ServiceCategory.order)
            .all()
        )
    
    def get_by_name(self, db: Session, *, name: str) -> Optional[ServiceCategory]:
        """Получить категорию по имени"""
        return db.query(self.model).filter(ServiceCategory.name == name).first()

crud_service_category = CRUDServiceCategory(ServiceCategory)