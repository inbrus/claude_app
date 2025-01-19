from pydantic import BaseModel
from typing import Optional

class AdminBase(BaseModel):
    telegram_id: str
    username: Optional[str] = None

class AdminCreate(AdminBase):
    pass

class Admin(AdminBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True