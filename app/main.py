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
import asyncio
from app.crud.crud_admin import crud_admin
from app.db.session import SessionLocal
from app.bot.admin_handlers import (
    manage_services, admin_menu, view_appointments,
    start_add_service, enter_service_name, enter_service_description,
    skip_description, enter_service_price, enter_service_duration,
    confirm_service, edit_service, toggle_service, delete_service,
    confirm_delete_service, start_edit_field, process_edit_field,
    ENTER_SERVICE_NAME, ENTER_SERVICE_DESCRIPTION, ENTER_SERVICE_PRICE,
    ENTER_SERVICE_DURATION, CONFIRM_SERVICE, EDIT_SERVICE_FIELD,
    update_appointment_status, edit_appointment_time,
    edit_appointment_service, change_appointment_date,
    update_appointment_time, update_appointment_service,
    update_filters, manage_appointment
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
from app.bot.client_handlers import (
    select_service, select_date, select_time, client_menu,
    my_appointments, manage_client_appointment,
    client_cancel_appointment, confirm_client_cancel,
    start_reschedule_appointment, select_reschedule_date,
    confirm_reschedule, start_service_search, process_service_search,
    filter_services_by_category, reset_service_filters
)
from app.bot.notifications import (
    notify_admin_new_appointment,
    notify_admin_appointment_cancelled,
    notify_client_status_change,
    check_upcoming_appointments
)

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Создание FastAPI приложения
app = FastAPI(title=settings.PROJECT_NAME)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Создание бота
bot = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

async def start_command(update: Update, context):
    """Обработка команды /start"""
    keyboard = [
        [InlineKeyboardButton("Записаться", callback_data="select_service")],
        [InlineKeyboardButton("Мои записи", callback_data="my_appointments")]
    ]
    
    # Проверяем, является ли пользователь администратором
    db = SessionLocal()
    try:
        admin = crud_admin.get_by_telegram_id(db, str(update.effective_user.id))
        if admin and admin.is_active:
            keyboard.append([InlineKeyboardButton("Админ панель", callback_data="admin_menu")])
            context.user_data['admin_id'] = admin.id
    finally:
        db.close()
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Добро пожаловать! Выберите действие:",
        reply_markup=reply_markup
    )

async def make_admin_command(update: Update, context):
    """Обработка команды /make_admin"""
    db = SessionLocal()
    try:
        # Проверяем, существует ли уже администратор
        existing_admin = crud_admin.get_first(db)
        if existing_admin:
            await update.message.reply_text(
                "Администратор уже существует. Команда недоступна."
            )
            return
        
        # Создаем нового администратора
        admin = crud_admin.create_admin(
            db,
            telegram_id=str(update.effective_user.id),
            username=update.effective_user.username or "Unknown"
        )
        
        if admin:
            context.user_data['admin_id'] = admin.id
            await update.message.reply_text(
                "Вы успешно назначены администратором!"
            )
        else:
            await update.message.reply_text(
                "Произошла ошибка при назначении администратором."
            )
    finally:
        db.close()

async def button_callback(update: Update, context):
    """Обработка нажатий на кнопки"""
    query = update.callback_query
    
    if query.data == 'select_service':
        await select_service(update, context)
    elif query.data.startswith('select_service_'):
        await select_date(update, context)
    elif query.data.startswith('select_date_'):
        await select_time(update, context)
    elif query.data == 'my_appointments':
        await my_appointments(update, context)
    elif query.data == 'manage_schedule':
        await manage_schedule(update, context)
    elif query.data.startswith('edit_day_'):
        await edit_day(update, context)
    elif query.data.startswith('toggle_day_'):
        await toggle_day(update, context)
    elif query.data.startswith('manage_client_appointment_'):
        await manage_client_appointment(update, context)
    elif query.data.startswith('confirm_appointment_') or query.data.startswith('cancel_appointment_'):
        await update_appointment_status(update, context)
    elif query.data.startswith('edit_appointment_time_'):
        await edit_appointment_time(update, context)
    elif query.data.startswith('edit_appointment_service_'):
        await edit_appointment_service(update, context)
    elif query.data.startswith('change_date_'):
        await change_appointment_date(update, context)
    elif query.data.startswith('update_time_'):
        await update_appointment_time(update, context)
    elif query.data.startswith('update_service_'):
        await update_appointment_service(update, context)
    elif query.data.startswith('filter_'):
        await update_filters(update, context)
    elif query.data.startswith('manage_appointment_'):
        await manage_appointment(update, context)
    elif query.data.startswith('reschedule_appointment_'):
        await start_reschedule_appointment(update, context)
    elif query.data.startswith('reschedule_date_'):
        await select_reschedule_date(update, context)
    elif query.data.startswith('confirm_reschedule_'):
        await confirm_reschedule(update, context)
    elif query.data.startswith('client_cancel_appointment_'):
        await client_cancel_appointment(update, context)
    elif query.data.startswith('confirm_client_cancel_'):
        await confirm_client_cancel(update, context)
    elif query.data == 'admin_menu':
        await admin_menu(update, context)
    elif query.data == 'view_appointments':
        await view_appointments(update, context)
    elif query.data == 'manage_services':
        await manage_services(update, context)
    elif query.data.startswith('edit_service_'):
        await edit_service(update, context)
    elif query.data.startswith('toggle_service_'):
        await toggle_service(update, context)
    elif query.data.startswith('delete_service_'):
        await delete_service(update, context)
    elif query.data.startswith('confirm_delete_'):
        await confirm_delete_service(update, context)
    elif query.data == 'client_menu':
        await client_menu(update, context)
    elif query.data.startswith('filter_category_'):
        await filter_services_by_category(update, context)
    elif query.data == 'reset_service_filters':
        await reset_service_filters(update, context)

# Создаем обработчик диалога добавления услуги
add_service_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_add_service, pattern='^add_service$')],
    states={
        ENTER_SERVICE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_service_name)],
        ENTER_SERVICE_DESCRIPTION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, enter_service_description),
            CallbackQueryHandler(skip_description, pattern='^skip$')
        ],
        ENTER_SERVICE_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_service_price)],
        ENTER_SERVICE_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_service_duration)],
        CONFIRM_SERVICE: [CallbackQueryHandler(confirm_service, pattern='^confirm_service$')]
    },
    fallbacks=[
        CallbackQueryHandler(manage_services, pattern='^manage_services$')
    ]
)

# Создаем обработчик диалога редактирования услуги
edit_field_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_edit_field, pattern='^edit_field_\d+_\w+$')],
    states={
        EDIT_SERVICE_FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_edit_field)]
    },
    fallbacks=[
        CallbackQueryHandler(edit_service, pattern='^edit_service_\d+$')
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

# Создаем обработчик диалога поиска услуг
search_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_service_search, pattern='^search_services$')],
    states={
        "waiting_search_query": [MessageHandler(filters.TEXT & ~filters.COMMAND, process_service_search)]
    },
    fallbacks=[CallbackQueryHandler(select_service, pattern='^select_service$')]
)

# Регистрируем обработчики
bot.add_handler(CommandHandler("start", start_command))
bot.add_handler(CommandHandler("make_admin", make_admin_command))
bot.add_handler(add_service_handler)
bot.add_handler(edit_field_handler)
bot.add_handler(schedule_handler)
bot.add_handler(search_handler)
bot.add_handler(CallbackQueryHandler(button_callback))

@app.post("/webhook")
async def webhook(request: Request):
    """Обработка вебхуков от Telegram"""
    try:
        data = await request.json()
        update = Update.de_json(data, bot.bot)
        await bot.process_update(update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        raise

@app.on_event("startup")
async def startup_event():
    """Настройка вебхука и запуск фоновых задач при запуске"""
    try:
        await bot.initialize()
        webhook_url = f"{settings.WEBAPP_URL}/webhook"
        await bot.bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook set to {webhook_url}")
        
        # Запускаем проверку предстоящих записей в фоновом режиме
        asyncio.create_task(check_upcoming_appointments(bot.bot))
        logger.info("Started checking upcoming appointments")
    except Exception as e:
        logger.error(f"Error during startup: {e}", exc_info=True)
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при выключении"""
    try:
        await bot.shutdown()
    except Exception as e:
        logger.error(f"Error during shutdown: {e}", exc_info=True)
        raise
