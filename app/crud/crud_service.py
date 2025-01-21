from typing import List, Optional, Dict, Any
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload
from app.crud.base import CRUDBase
from app.models.models import Service, ServiceCategory
from app.schemas.service import ServiceCreate, ServiceUpdate, ServiceList

class CRUDService(CRUDBase[Service, ServiceCreate, ServiceUpdate]):
    def get_active(self, db: Session) -> List[Service]:
        """Получить все активные услуги"""
        return (
            db.query(self.model)
            .options(joinedload(Service.category))
            .filter(Service.is_active == True)
            .order_by(Service.category_id, Service.order)
            .all()
        )
    
    def get_by_category(
        self, db: Session, *, category_id: int, active_only: bool = True
    ) -> List[Service]:
        """Получить услуги по категории"""
        query = db.query(self.model).filter(Service.category_id == category_id)
        if active_only:
            query = query.filter(Service.is_active == True)
        return query.order_by(Service.order).all()
    
    def search(
        self, db: Session, *, query: str, category_id: Optional[int] = None
    ) -> List[Service]:
        """Поиск услуг по названию или описанию"""
        search_filter = or_(
            Service.name.ilike(f"%{query}%"),
            Service.description.ilike(f"%{query}%")
        )
        
        db_query = (
            db.query(self.model)
            .options(joinedload(Service.category))
            .filter(search_filter, Service.is_active == True)
        )
        
        if category_id is not None:
            db_query = db_query.filter(Service.category_id == category_id)
        
        return db_query.order_by(Service.category_id, Service.order).all()
    
    def get_services_with_categories(self, db: Session) -> ServiceList:
        """Получить список услуг, сгруппированный по категориям"""
        categories = (
            db.query(ServiceCategory)
            .filter(ServiceCategory.is_active == True)
            .order_by(ServiceCategory.order)
            .all()
        )
        
        services = (
            db.query(self.model)
            .options(joinedload(Service.category))
            .filter(Service.is_active == True)
            .order_by(Service.category_id, Service.order)
            .all()
        )
        
        return ServiceList(categories=categories, services=services)

crud_service = CRUDService(Service)