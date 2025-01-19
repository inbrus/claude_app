from fastapi import FastAPI, Request
from app.core.config import settings
from fastapi.middleware.cors import CORSMiddleware
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
import logging
from app.crud.crud_admin import crud_admin
from app.db.session import SessionLocal

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/docs"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Создаем экземпляр бота
bot = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

async def start_command(update: Update, context):
    """Обработчик команды /start"""
    db = SessionLocal()
    try:
        user_id = update.message.from_user.id
        admin = await crud_admin.get_by_telegram_id(db, str(user_id))
        
        if admin:
            # Если пользователь админ
            keyboard = [
                [InlineKeyboardButton("Управление услугами", callback_data='manage_services')],
                [InlineKeyboardButton("Управление расписанием", callback_data='manage_schedule')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "Добро пожаловать в панель администратора!\n"
                "Выберите действие:",
                reply_markup=reply_markup
            )
        else:
            # Если обычный пользователь
            keyboard = [
                [InlineKeyboardButton("Записаться", callback_data='book_service')],
                [InlineKeyboardButton("Мои записи", callback_data='my_appointments')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "Добро пожаловать! Я помогу вам записаться на услуги.\n"
                "Выберите действие:",
                reply_markup=reply_markup
            )
    except Exception as e:
        logger.error(f"Error in start command: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")
    finally:
        db.close()

async def make_admin_command(update: Update, context):
    """Обработчик команды /make_admin"""
    db = SessionLocal()
    try:
        user_id = update.message.from_user.id
        admin = await crud_admin.get_by_telegram_id(db, str(user_id))
        
        if admin:
            await update.message.reply_text("Вы уже являетесь администратором.")
        else:
            new_admin = await crud_admin.create(
                db,
                telegram_id=str(user_id),
                username=update.message.from_user.username or "Unknown"
            )
            if new_admin:
                await update.message.reply_text(
                    "Вы успешно назначены администратором!\n"
                    "Используйте /start для доступа к панели управления."
                )
            else:
                await update.message.reply_text("Произошла ошибка при назначении администратором.")
    except Exception as e:
        logger.error(f"Error in make_admin command: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")
    finally:
        db.close()

async def button_callback(update: Update, context):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'book_service':
        await query.message.reply_text("Выберите услугу для записи:")
    elif query.data == 'my_appointments':
        await query.message.reply_text("Ваши записи:")
    elif query.data == 'manage_services':
        await query.message.reply_text("Управление услугами:")
    elif query.data == 'manage_schedule':
        await query.message.reply_text("Управление расписанием:")

# Регистрируем обработчики
bot.add_handler(CommandHandler("start", start_command))
bot.add_handler(CommandHandler("make_admin", make_admin_command))
bot.add_handler(CallbackQueryHandler(button_callback))

@app.post("/webhook")
async def webhook(request: Request):
    """Обработка вебхуков от Telegram"""
    try:
        data = await request.json()
        logger.info(f"Received webhook data: {data}")
        
        if not bot.running:
            await bot.initialize()
        
        update = Update.de_json(data, bot.bot)
        await bot.process_update(update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        raise

@app.on_event("startup")
async def startup_event():
    """Настройка вебхука при запуске"""
    try:
        await bot.initialize()
        webhook_url = f"{settings.WEBAPP_URL}/webhook"
        await bot.bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook set to {webhook_url}")
    except Exception as e:
        logger.error(f"Error during startup: {e}", exc_info=True)
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при выключении"""
    if bot.running:
        await bot.shutdown()

@app.get("/")
async def root():
    return {"message": "Telegram Booking Mini App API"}