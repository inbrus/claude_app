from pydantic import BaseModel, Field
from typing import Optional, List

class ServiceCategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    order: int = 0
    is_active: bool = True

class ServiceCategoryCreate(ServiceCategoryBase):
    pass

class ServiceCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = None
    is_active: Optional[bool] = None

class ServiceCategory(ServiceCategoryBase):
    id: int

    class Config:
        from_attributes = True

class ServiceBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float = Field(ge=0)
    duration: int = Field(ge=5, description="Длительность услуги в минутах")
    category_id: Optional[int] = None
    order: int = 0

class ServiceCreate(ServiceBase):
    pass

class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)
    duration: Optional[int] = Field(None, ge=5)
    category_id: Optional[int] = None
    order: Optional[int] = None
    is_active: Optional[bool] = None

class Service(ServiceBase):
    id: int
    is_active: bool
    category: Optional[ServiceCategory] = None

    class Config:
        from_attributes = True

class ServiceWithCategory(Service):
    category_name: Optional[str] = None

class ServiceList(BaseModel):
    categories: List[ServiceCategory]
    services: List[Service]