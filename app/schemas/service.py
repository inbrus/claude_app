from pydantic import BaseModel, Field
from typing import Optional

class ServiceBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float = Field(ge=0)
    duration: int = Field(ge=5, description="Длительность услуги в минутах")

class ServiceCreate(ServiceBase):
    pass

class ServiceUpdate(ServiceBase):
    name: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)
    duration: Optional[int] = Field(None, ge=5)

class Service(ServiceBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True