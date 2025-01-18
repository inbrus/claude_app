from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
)
from datetime import datetime, timedelta
from app.crud.crud_admin import crud_admin
from app.crud.crud_service import crud_service
from app.crud.crud_appointment import crud_appointment
from app.schemas.admin import AdminCreate
from app.schemas.appointment import AppointmentCreate
from app.db.session import SessionLocal

# Состояния разговора
SELECTING_SERVICE, SELECTING_DATE, SELECTING_TIME, CONFIRMING = range(4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало взаимодействия с ботом"""
    db = SessionLocal()
    try:
        user = update.effective_user
        admin = crud_admin.get_by_telegram_id(db, str(user.id))
        
        if admin:
            keyboard = [
                [InlineKeyboardButton("Управление услугами", callback_data="manage_services")],
                [InlineKeyboardButton("Просмотр записей", callback_data="view_appointments")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"Здравствуйте, {user.first_name}! Вы вошли как администратор.",
                reply_markup=reply_markup
            )
        else:
            keyboard = [
                [InlineKeyboardButton("Записаться", callback_data="book_appointment")],
                [InlineKeyboardButton("Мои записи", callback_data="my_appointments")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"Здравствуйте, {user.first_name}! Добро пожаловать в систему записи.",
                reply_markup=reply_markup
            )
    finally:
        db.close()

async def make_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сделать пользователя администратором"""
    db = SessionLocal()
    try:
        user = update.effective_user
        admin = crud_admin.get_by_telegram_id(db, str(user.id))
        
        if admin:
            await update.message.reply_text("Вы уже являетесь администратором.")
            return

        admin_in = AdminCreate(
            telegram_id=str(user.id),
            username=user.username
        )
        crud_admin.create(db, obj_in=admin_in)
        
        await update.message.reply_text("Вы успешно назначены администратором!")
    finally:
        db.close()

async def book_appointment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса записи"""
    db = SessionLocal()
    try:
        services = crud_service.get_active(db)
        keyboard = [
            [InlineKeyboardButton(service.name, callback_data=f"service_{service.id}")]
            for service in services
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.message.reply_text(
            "Выберите услугу:",
            reply_markup=reply_markup
        )
        return SELECTING_SERVICE
    finally:
        db.close()

def create_bot_application(token: str) -> Application:
    """Создание и настройка приложения бота"""
    application = Application.builder().token(token).build()
    
    # Базовые команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("make_admin", make_admin))
    
    # Обработчик записи
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(book_appointment, pattern="^book_appointment$")],
        states={
            SELECTING_SERVICE: [
                CallbackQueryHandler(book_appointment, pattern="^service_")
            ],
            SELECTING_DATE: [
                CallbackQueryHandler(book_appointment, pattern="^date_")
            ],
            SELECTING_TIME: [
                CallbackQueryHandler(book_appointment, pattern="^time_")
            ],
            CONFIRMING: [
                CallbackQueryHandler(book_appointment, pattern="^confirm_")
            ],
        },
        fallbacks=[CommandHandler("cancel", start)],
    )
    application.add_handler(conv_handler)
    
    return application