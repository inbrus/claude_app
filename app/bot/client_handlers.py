from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime, timedelta
from app.crud.crud_service import crud_service
from app.crud.crud_appointment import crud_appointment
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate
from app.db.session import SessionLocal

async def select_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор услуги для записи"""
    db = SessionLocal()
    try:
        services = crud_service.get_active(db)
        keyboard = []
        for service in services:
            keyboard.append([
                InlineKeyboardButton(
                    f"{service.name} - {service.price}₽",
                    callback_data=f"select_service_{service.id}"
                )
            ])
        keyboard.append([InlineKeyboardButton("« Отмена", callback_data="client_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.edit_text(
            "Выберите услугу:",
            reply_markup=reply_markup
        )
    finally:
        db.close()

async def select_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор даты для записи"""
    service_id = int(update.callback_query.data.split('_')[2])
    context.user_data['service_id'] = service_id
    
    # Создаем календарь на ближайшие 7 дней
    keyboard = []
    today = datetime.now()
    for i in range(7):
        date = today + timedelta(days=i)
        keyboard.append([
            InlineKeyboardButton(
                date.strftime("%d.%m.%Y"),
                callback_data=f"select_date_{date.strftime('%Y-%m-%d')}"
            )
        ])
    keyboard.append([InlineKeyboardButton("« Назад", callback_data="select_service")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.edit_text(
        "Выберите дату:",
        reply_markup=reply_markup
    )

async def select_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор времени для записи"""
    selected_date = datetime.strptime(
        update.callback_query.data.split('_')[2],
        '%Y-%m-%d'
    )
    context.user_data['selected_date'] = selected_date
    
    # Создаем временные слоты с 9:00 до 20:00 каждые 30 минут
    keyboard = []
    current_time = selected_date.replace(hour=9, minute=0)
    end_time = selected_date.replace(hour=20, minute=0)
    
    db = SessionLocal()
    try:
        while current_time <= end_time:
            # Проверяем, не занято ли время
            existing = crud_appointment.get_by_date_range(
                db,
                current_time,
                current_time + timedelta(minutes=30)
            )
            
            if not existing:
                keyboard.append([
                    InlineKeyboardButton(
                        current_time.strftime("%H:%M"),
                        callback_data=f"select_time_{current_time.strftime('%H:%M')}"
                    )
                ])
            
            current_time += timedelta(minutes=30)
        
        keyboard.append([InlineKeyboardButton("« Назад", callback_data="select_date")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.message.edit_text(
            "Выберите время:",
            reply_markup=reply_markup
        )
    finally:
        db.close()

async def confirm_appointment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение записи"""
    selected_time = update.callback_query.data.split('_')[2]
    selected_date = context.user_data['selected_date']
    service_id = context.user_data['service_id']
    
    appointment_time = selected_date.replace(
        hour=int(selected_time.split(':')[0]),
        minute=int(selected_time.split(':')[1])
    )
    
    db = SessionLocal()
    try:
        service = crud_service.get(db, id=service_id)
        user = update.effective_user
        
        appointment_in = AppointmentCreate(
            client_telegram_id=str(user.id),
            client_name=user.first_name,
            client_phone="Не указан",  # Здесь можно добавить запрос телефона
            service_id=service_id,
            appointment_time=appointment_time
        )
        
        appointment = crud_appointment.create(db, obj_in=appointment_in)
        
        text = (
            f"✅ Запись подтверждена!\n\n"
            f"Услуга: {service.name}\n"
            f"Дата: {appointment_time.strftime('%d.%m.%Y')}\n"
            f"Время: {appointment_time.strftime('%H:%M')}\n"
            f"Стоимость: {service.price}₽"
        )
        
        keyboard = [[InlineKeyboardButton("« Главное меню", callback_data="client_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.message.edit_text(
            text,
            reply_markup=reply_markup
        )
    finally:
        db.close()

async def my_appointments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Просмотр своих записей"""
    db = SessionLocal()
    try:
        user = update.effective_user
        appointments = crud_appointment.get_by_client(db, str(user.id))
        
        if not appointments:
            keyboard = [[InlineKeyboardButton("« Назад", callback_data="client_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.callback_query.message.edit_text(
                "У вас нет активных записей.",
                reply_markup=reply_markup
            )
            return
        
        text = "Ваши записи:\n\n"
        for apt in appointments:
            service = crud_service.get(db, id=apt.service_id)
            text += (
                f"📅 {apt.appointment_time.strftime('%d.%m.%Y %H:%M')}\n"
                f"💇‍♀️ {service.name}\n"
                f"💰 {service.price}₽\n"
                f"Status: {apt.status}\n\n"
            )
        
        keyboard = [
            [InlineKeyboardButton("« Назад", callback_data="client_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.edit_text(
            text,
            reply_markup=reply_markup
        )
    finally:
        db.close()

async def client_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню клиента"""
    keyboard = [
        [InlineKeyboardButton("Записаться", callback_data="select_service")],
        [InlineKeyboardButton("Мои записи", callback_data="my_appointments")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.edit_text(
        "Главное меню:",
        reply_markup=reply_markup
    )