from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime, timedelta
from app.crud.crud_service import crud_service
from app.crud.crud_appointment import crud_appointment
from app.schemas.service import ServiceCreate, ServiceUpdate
from app.db.session import SessionLocal

async def manage_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Управление услугами"""
    db = SessionLocal()
    try:
        services = crud_service.get_multi(db)
        keyboard = []
        for service in services:
            keyboard.append([
                InlineKeyboardButton(
                    f"{service.name} - {service.price}₽",
                    callback_data=f"edit_service_{service.id}"
                )
            ])
        keyboard.append([InlineKeyboardButton("➕ Добавить услугу", callback_data="add_service")])
        keyboard.append([InlineKeyboardButton("« Назад", callback_data="admin_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.edit_text(
            "Управление услугами:",
            reply_markup=reply_markup
        )
    finally:
        db.close()

async def view_appointments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Просмотр записей"""
    db = SessionLocal()
    try:
        # Получаем записи на сегодня и завтра
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        appointments = crud_appointment.get_by_date_range(db, today, tomorrow + timedelta(days=1))
        
        if not appointments:
            keyboard = [[InlineKeyboardButton("« Назад", callback_data="admin_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.callback_query.message.edit_text(
                "На ближайшие дни записей нет.",
                reply_markup=reply_markup
            )
            return
        
        text = "Записи на ближайшие дни:\n\n"
        for apt in appointments:
            service = crud_service.get(db, id=apt.service_id)
            text += (
                f"📅 {apt.appointment_time.strftime('%d.%m.%Y %H:%M')}\n"
                f"👤 {apt.client_name}\n"
                f"📞 {apt.client_phone}\n"
                f"💇‍♀️ {service.name}\n"
                f"Status: {apt.status}\n\n"
            )
        
        keyboard = [
            [InlineKeyboardButton("« Назад", callback_data="admin_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.edit_text(
            text,
            reply_markup=reply_markup
        )
    finally:
        db.close()

async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню администратора"""
    keyboard = [
        [InlineKeyboardButton("Управление услугами", callback_data="manage_services")],
        [InlineKeyboardButton("Просмотр записей", callback_data="view_appointments")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.edit_text(
        "Меню администратора:",
        reply_markup=reply_markup
    )