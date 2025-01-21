from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime, timedelta
from app.crud.crud_appointment import crud_appointment
from app.crud.crud_admin import crud_admin
from app.db.session import SessionLocal
import asyncio
import logging

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

def format_date(date: datetime) -> str:
    """Форматирование даты"""
    return date.strftime("%d.%m.%Y")

def format_time(time: datetime) -> str:
    """Форматирование времени"""
    return time.strftime("%H:%M")

async def send_notification(bot, chat_id: str, text: str, reply_markup=None):
    """Отправка уведомления в Telegram"""
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error sending notification to {chat_id}: {e}")

async def notify_admin_appointment_cancelled(bot, admin_id: int, appointment_id: int):
    """Уведомление администратора об отмене записи"""
    db = SessionLocal()
    try:
        admin = crud_admin.get(db, id=admin_id)
        appointment = crud_appointment.get(db, id=appointment_id)
        
        if not admin or not appointment:
            return
        
        text = (
            "❌ <b>Запись отменена клиентом!</b>\n\n"
            f"Клиент: {appointment.client_name}\n"
            f"Телефон: {appointment.client_phone}\n"
            f"Услуга: {appointment.service.name}\n"
            f"Дата: {format_date(appointment.appointment_time)}\n"
            f"Время: {format_time(appointment.appointment_time)}"
        )
        
        keyboard = [[
            InlineKeyboardButton(
                "⚙️ Управление записью",
                callback_data=f"manage_appointment_{appointment_id}"
            )
        ]]
        
        await send_notification(
            bot,
            chat_id=admin.telegram_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    finally:
        db.close()

async def notify_admin_new_appointment(bot, admin_id: int, appointment_id: int):
    """Уведомление администратора о новой записи"""
    db = SessionLocal()
    try:
        admin = crud_admin.get(db, id=admin_id)
        appointment = crud_appointment.get(db, id=appointment_id)
        
        if not admin or not appointment:
            return
        
        text = (
            "🔔 <b>Новая запись!</b>\n\n"
            f"Клиент: {appointment.client_name}\n"
            f"Телефон: {appointment.client_phone}\n"
            f"Услуга: {appointment.service.name}\n"
            f"Дата: {format_date(appointment.appointment_time)}\n"
            f"Время: {format_time(appointment.appointment_time)}\n\n"
            f"Статус: {appointment.status}"
        )
        
        keyboard = [
            [
                InlineKeyboardButton(
                    "✅ Подтвердить",
                    callback_data=f"confirm_appointment_{appointment_id}"
                ),
                InlineKeyboardButton(
                    "❌ Отменить",
                    callback_data=f"cancel_appointment_{appointment_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "⚙️ Управление записью",
                    callback_data=f"manage_appointment_{appointment_id}"
                )
            ]
        ]
        
        await send_notification(
            bot,
            chat_id=admin.telegram_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    finally:
        db.close()

async def notify_client_status_change(bot, appointment_id: int):
    """Уведомление клиента об изменении статуса записи"""
    db = SessionLocal()
    try:
        appointment = crud_appointment.get(db, id=appointment_id)
        if not appointment:
            return
        
        status_text = {
            "confirmed": "✅ подтверждена",
            "cancelled": "❌ отменена"
        }.get(appointment.status)
        
        if not status_text:
            return
        
        text = (
            f"Ваша запись {status_text}!\n\n"
            f"Услуга: {appointment.service.name}\n"
            f"Дата: {format_date(appointment.appointment_time)}\n"
            f"Время: {format_time(appointment.appointment_time)}"
        )
        
        if appointment.status == "confirmed":
            text += "\n\nЖдём вас!"
        
        keyboard = [[
            InlineKeyboardButton("Мои записи", callback_data="my_appointments")
        ]]
        
        await send_notification(
            bot,
            chat_id=appointment.client_telegram_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    finally:
        db.close()

async def send_reminder(bot, appointment_id: int, hours_before: int):
    """Отправка напоминания о записи"""
    db = SessionLocal()
    try:
        appointment = crud_appointment.get(db, id=appointment_id)
        if not appointment or appointment.status != "confirmed":
            return
        
        if hours_before == 24:
            time_text = "завтра"
        elif hours_before == 2:
            time_text = "через 2 часа"
        else:
            return
        
        text = (
            f"⏰ Напоминаем о записи {time_text}!\n\n"
            f"Услуга: {appointment.service.name}\n"
            f"Дата: {format_date(appointment.appointment_time)}\n"
            f"Время: {format_time(appointment.appointment_time)}"
        )
        
        keyboard = [[
            InlineKeyboardButton("Отменить запись", callback_data=f"cancel_appointment_{appointment_id}")
        ]]
        
        await send_notification(
            bot,
            chat_id=appointment.client_telegram_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    finally:
        db.close()

async def check_upcoming_appointments(bot):
    """Проверка предстоящих записей и отправка напоминаний"""
    while True:
        try:
            db = SessionLocal()
            now = datetime.now()
            
            # Получаем записи на ближайшие 24 часа
            appointments = crud_appointment.get_by_date_range(
                db,
                start_date=now,
                end_date=now + timedelta(days=1),
                status="confirmed"
            )
            
            for appointment in appointments:
                time_until = appointment.appointment_time - now
                hours_until = time_until.total_seconds() / 3600
                
                # Напоминание за 24 часа
                if 23.9 <= hours_until <= 24.1:
                    await send_reminder(bot, appointment.id, 24)
                
                # Напоминание за 2 часа
                elif 1.9 <= hours_until <= 2.1:
                    await send_reminder(bot, appointment.id, 2)
        
        except Exception as e:
            logger.error(f"Error in check_upcoming_appointments: {e}")
        finally:
            db.close()
        
        # Проверяем каждые 5 минут
        await asyncio.sleep(300)