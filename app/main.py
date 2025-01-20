from fastapi import FastAPI, Request
from app.core.config import settings
from fastapi.middleware.cors import CORSMiddleware
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters
)
import logging
import re
from app.crud.crud_admin import crud_admin
from app.db.session import SessionLocal
from app.bot.admin_handlers import (
    manage_services, admin_menu, view_appointments,
    start_add_service, enter_service_name, enter_service_description,
    skip_description, enter_service_price, enter_service_duration,
    confirm_service, edit_service, toggle_service, delete_service,
    confirm_delete_service, start_edit_field, process_edit_field,
    ENTER_SERVICE_NAME, ENTER_SERVICE_DESCRIPTION, ENTER_SERVICE_PRICE,
    ENTER_SERVICE_DURATION, CONFIRM_SERVICE, EDIT_SERVICE_FIELD
)
from app.bot.schedule_handlers import (
    manage_schedule, edit_day, start_set_working,
    process_start_time, process_end_time,
    process_break_start, process_break_end,
    confirm_schedule, toggle_day,
    ENTER_START_TIME, ENTER_END_TIME,
    ENTER_BREAK_START, ENTER_BREAK_END,
    CONFIRM_SCHEDULE
)

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
        await manage_services(update, context)
    elif query.data == 'manage_schedule':
        await manage_schedule(update, context)
    elif query.data.startswith('edit_day_'):
        await edit_day(update, context)
    elif query.data.startswith('toggle_day_'):
        await toggle_day(update, context)
    elif query.data == 'admin_menu':
        await admin_menu(update, context)
    elif query.data == 'view_appointments':
        await view_appointments(update, context)
    elif query.data == 'add_service':
        await start_add_service(update, context)
    elif query.data.startswith('edit_service_'):
        await edit_service(update, context)
    elif query.data.startswith('toggle_service_'):
        await toggle_service(update, context)
    elif query.data.startswith('delete_service_'):
        await delete_service(update, context)
    elif query.data.startswith('confirm_delete_'):
        await confirm_delete_service(update, context)
    elif any(query.data.startswith(f'edit_{field}_') for field in ['name', 'description', 'price', 'duration']):
        await start_edit_field(update, context)

# Создаем обработчик диалога добавления услуги
add_service_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_add_service, pattern='^add_service$')],
    states={
        ENTER_SERVICE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_service_name)],
        ENTER_SERVICE_DESCRIPTION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, enter_service_description),
            CommandHandler('skip', skip_description)
        ],
        ENTER_SERVICE_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_service_price)],
        ENTER_SERVICE_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_service_duration)],
        CONFIRM_SERVICE: [CallbackQueryHandler(confirm_service, pattern='^confirm_service$')]
    },
    fallbacks=[CallbackQueryHandler(manage_services, pattern='^manage_services$')]
)

# Создаем обработчик диалога редактирования полей услуги
edit_field_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(
            start_edit_field,
            pattern='^edit_(name|description|price|duration)_\d+$'
        )
    ],
    states={
        EDIT_SERVICE_FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_edit_field)]
    },
    fallbacks=[
        CallbackQueryHandler(
            edit_service,
            pattern='^edit_service_\d+$'
        )
    ]
)

# Создаем обработчик диалога настройки расписания
schedule_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_set_working, pattern='^set_working_\d+$')],
    states={
        ENTER_START_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_start_time)],
        ENTER_END_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_end_time)],
        ENTER_BREAK_START: [
            CallbackQueryHandler(process_break_start, pattern='^set_break$'),
            CallbackQueryHandler(confirm_schedule, pattern='^skip_break$')
        ],
        ENTER_BREAK_END: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_break_end)],
        CONFIRM_SCHEDULE: [CallbackQueryHandler(confirm_schedule, pattern='^confirm_schedule$')]
    },
    fallbacks=[
        CallbackQueryHandler(edit_day, pattern='^edit_day_\d+$'),
        CallbackQueryHandler(manage_schedule, pattern='^manage_schedule$')
    ]
)

# Регистрируем обработчики
bot.add_handler(CommandHandler("start", start_command))
bot.add_handler(CommandHandler("make_admin", make_admin_command))
bot.add_handler(add_service_handler)
bot.add_handler(edit_field_handler)
bot.add_handler(schedule_handler)
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