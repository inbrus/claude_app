from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Telegram Booking Mini App"
    DATABASE_URL: str
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    WEBAPP_URL: str = "https://bookingfortomorrow.ru"
    
    # Добавляем поля для MySQL
    MYSQL_USER: str
    MYSQL_PASSWORD: str
    MYSQL_DB: str

    model_config = SettingsConfigDict(
        env_file='.env',
        extra='allow',
        env_file_encoding='utf-8'
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.DATABASE_URL:
            self.DATABASE_URL = f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@localhost/{self.MYSQL_DB}"

settings = Settings()