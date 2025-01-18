from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from app.core.config import settings
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
)
from app.crud.crud_admin import crud_admin
from app.schemas.admin import AdminCreate
from app.db.session import SessionLocal
from .admin_handlers import manage_services, view_appointments, admin_menu
from .client_handlers import (
    select_service,
    select_date,
    select_time,
    confirm_appointment,
    my_appointments,
    client_menu
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало взаимодействия с ботом"""
    db = SessionLocal()
    try:
        user = update.effective_user
        admin = crud_admin.get_by_telegram_id(db, str(user.id))
        
        if admin:
            keyboard = [
                [InlineKeyboardButton("Открыть панель управления", web_app=WebAppInfo(url=f"{settings.WEBAPP_URL}/admin"))],
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
                [InlineKeyboardButton("Записаться онлайн", web_app=WebAppInfo(url=settings.WEBAPP_URL))],
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

def create_bot_application(token: str) -> Application:
    """Создание и настройка приложения бота"""
    application = Application.builder().token(token).build()
    
    # Базовые команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("make_admin", make_admin))
    
    # Обработчики для администраторов
    application.add_handler(CallbackQueryHandler(manage_services, pattern="^manage_services$"))
    application.add_handler(CallbackQueryHandler(view_appointments, pattern="^view_appointments$"))
    application.add_handler(CallbackQueryHandler(admin_menu, pattern="^admin_menu$"))
    
    # Обработчики для клиентов
    application.add_handler(CallbackQueryHandler(select_service, pattern="^select_service"))
    application.add_handler(CallbackQueryHandler(select_date, pattern="^select_date"))
    application.add_handler(CallbackQueryHandler(select_time, pattern="^select_time"))
    application.add_handler(CallbackQueryHandler(confirm_appointment, pattern="^confirm"))
    application.add_handler(CallbackQueryHandler(my_appointments, pattern="^my_appointments$"))
    application.add_handler(CallbackQueryHandler(client_menu, pattern="^client_menu$"))
    
    return application