from fastapi import FastAPI
from app.core.config import settings
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.bot.handlers import create_bot_application
import asyncio
import logging

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url="/api/v1/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Telegram Booking Mini App API"}

@app.on_event("startup")
async def startup_event():
    if settings.TELEGRAM_BOT_TOKEN:
        bot_app = create_bot_application(settings.TELEGRAM_BOT_TOKEN)
        asyncio.create_task(bot_app.run_polling())