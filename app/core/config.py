from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Telegram Booking Mini App"
    DATABASE_URL: str = "postgresql://user:password@localhost/booking_db"
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    WEBAPP_URL: str = "http://localhost"
    
    class Config:
        env_file = ".env"

settings = Settings()