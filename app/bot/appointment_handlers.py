from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from datetime import datetime, timedelta
from app.crud.crud_appointment import crud_appointment
from app.crud.crud_service import crud_service
from app.crud.crud_admin import crud_admin
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate
from app.db.session import SessionLocal

# Состояния диалога
(
    SELECT_SERVICE,
    SELECT_DATE,
    SELECT_TIME,
    ENTER_NAME,
    ENTER_PHONE,
    CONFIRM_APPOINTMENT
) = range(6)

# Временное хранилище данных
appointment_data = {}

def format_date(date: datetime) -> str:
    """Форматирование даты"""
    return date.strftime("%d.%m.%Y")

def format_time(time: datetime) -> str:
    """Форматирование времени"""
    return time.strftime("%H:%M")

async def view_appointments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Просмотр записей"""
    db = SessionLocal()
    try:
        # Получаем записи на сегодня и завтра
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        admin_id = context.user_data.get('admin_id')
        
        appointments = crud_appointment.get_by_date_range(
            db,
            start_date=today,
            end_date=tomorrow + timedelta(days=1),
            admin_id=admin_id
        )
        
        if not appointments:
            keyboard = [[InlineKeyboardButton("« Назад", callback_data="admin_menu")]]
            await update.callback_query.message.edit_text(
                "На ближайшие дни записей нет.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        # Группируем записи по дням
        appointments_by_day = {}
        for apt in appointments:
            day = apt.appointment_time.date()
            if day not in appointments_by_day:
                appointments_by_day[day] = []
            appointments_by_day[day].append(apt)
        
        # Формируем текст сообщения
        text = "Записи на ближайшие дни:\n\n"
        for day, day_appointments in appointments_by_day.items():
            text += f"📅 {format_date(day)}:\n"
            for apt in sorted(day_appointments, key=lambda x: x.appointment_time):
                text += (
                    f"⏰ {format_time(apt.appointment_time)} - {apt.client_name}\n"
                    f"📞 {apt.client_phone or 'нет телефона'}\n"
                    f"💇‍♀️ {apt.service.name}\n"
                    f"Статус: {apt.status}\n\n"
                )
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="view_appointments")],
            [InlineKeyboardButton("« Назад", callback_data="admin_menu")]
        ]
        
        await update.callback_query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    finally:
        db.close()

async def start_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса записи"""
    db = SessionLocal()
    try:
        services = crud_service.get_multi(db)
        active_services = [s for s in services if s.is_active]
        
        if not active_services:
            await update.callback_query.message.edit_text(
                "К сожалению, сейчас нет доступных услуг.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Назад", callback_data="start")
                ]])
            )
            return ConversationHandler.END
        
        keyboard = []
        for service in active_services:
            keyboard.append([
                InlineKeyboardButton(
                    f"{service.name} - {service.price}₽",
                    callback_data=f"select_service_{service.id}"
                )
            ])
        keyboard.append([InlineKeyboardButton("« Отмена", callback_data="start")])
        
        await update.callback_query.message.edit_text(
            "Выберите услугу:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return SELECT_SERVICE
    finally:
        db.close()

async def select_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор услуги"""
    query = update.callback_query
    service_id = int(query.data.split('_')[-1])
    user_id = query.from_user.id
    
    db = SessionLocal()
    try:
        service = crud_service.get(db, id=service_id)
        if not service or not service.is_active:
            await query.message.edit_text(
                "Извините, эта услуга больше недоступна.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Назад", callback_data="book_service")
                ]])
            )
            return ConversationHandler.END
        
        # Сохраняем выбранную услугу
        appointment_data[user_id] = {
            'service_id': service_id,
            'service_name': service.name,
            'service_duration': service.duration
        }
        
        # Показываем календарь на ближайшие дни
        today = datetime.now().date()
        keyboard = []
        for i in range(14):  # Показываем записи на 2 недели вперед
            date = today + timedelta(days=i)
            keyboard.append([
                InlineKeyboardButton(
                    format_date(date),
                    callback_data=f"select_date_{date.isoformat()}"
                )
            ])
        keyboard.append([InlineKeyboardButton("« Назад", callback_data="book_service")])
        
        await query.message.edit_text(
            f"Выбрана услуга: {service.name}\n"
            f"Длительность: {service.duration} минут\n"
            f"Стоимость: {service.price}₽\n\n"
            f"Выберите дату:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return SELECT_DATE
    finally:
        db.close()

async def select_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор даты"""
    query = update.callback_query
    date_str = query.data.split('_')[-1]
    user_id = query.from_user.id
    
    if user_id not in appointment_data:
        await query.message.edit_text(
            "Произошла ошибка. Начните запись заново.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« В начало", callback_data="book_service")
            ]])
        )
        return ConversationHandler.END
    
    selected_date = datetime.fromisoformat(date_str)
    appointment_data[user_id]['date'] = selected_date
    
    db = SessionLocal()
    try:
        # Получаем первого доступного администратора
        admin = crud_admin.get_first_active(db)
        if not admin:
            await query.message.edit_text(
                "Извините, в данный момент нет доступных мастеров.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Назад", callback_data="book_service")
                ]])
            )
            return ConversationHandler.END
        
        appointment_data[user_id]['admin_id'] = admin.id
        
        # Получаем доступные слоты
        available_slots = crud_appointment.get_available_slots(
            db,
            admin_id=admin.id,
            date=selected_date,
            service_duration=appointment_data[user_id]['service_duration']
        )
        
        if not available_slots:
            await query.message.edit_text(
                "К сожалению, на эту дату нет свободных окон.\n"
                "Пожалуйста, выберите другую дату:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« К выбору даты", callback_data=f"select_service_{appointment_data[user_id]['service_id']}")
                ]])
            )
            return SELECT_DATE
        
        # Показываем доступные слоты
        keyboard = []
        for slot in available_slots:
            keyboard.append([
                InlineKeyboardButton(
                    format_time(slot),
                    callback_data=f"select_time_{slot.isoformat()}"
                )
            ])
        keyboard.append([
            InlineKeyboardButton("« К выбору даты", callback_data=f"select_service_{appointment_data[user_id]['service_id']}")
        ])
        
        await query.message.edit_text(
            f"Выбрана дата: {format_date(selected_date)}\n"
            f"Выберите удобное время:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return SELECT_TIME
    finally:
        db.close()

async def select_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор времени"""
    query = update.callback_query
    time_str = query.data.split('_')[-1]
    user_id = query.from_user.id
    
    if user_id not in appointment_data:
        await query.message.edit_text(
            "Произошла ошибка. Начните запись заново.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« В начало", callback_data="book_service")
            ]])
        )
        return ConversationHandler.END
    
    appointment_time = datetime.fromisoformat(time_str)
    appointment_data[user_id]['appointment_time'] = appointment_time
    
    await query.message.edit_text(
        "Введите ваше имя:",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("« Отмена", callback_data="book_service")
        ]])
    )
    return ENTER_NAME

async def enter_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод имени"""
    user_id = update.message.from_user.id
    name = update.message.text
    
    if len(name) > 100:
        await update.message.reply_text(
            "Имя слишком длинное. Пожалуйста, введите более короткое имя:"
        )
        return ENTER_NAME
    
    appointment_data[user_id]['client_name'] = name
    
    await update.message.reply_text(
        "Введите ваш номер телефона:",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("« Отмена", callback_data="book_service")
        ]])
    )
    return ENTER_PHONE

async def enter_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод телефона"""
    user_id = update.message.from_user.id
    phone = update.message.text
    
    if len(phone) > 20:
        await update.message.reply_text(
            "Номер телефона слишком длинный. Пожалуйста, проверьте правильность ввода:"
        )
        return ENTER_PHONE
    
    appointment_data[user_id]['client_phone'] = phone
    
    # Показываем сводку для подтверждения
    data = appointment_data[user_id]
    text = (
        f"Проверьте данные записи:\n\n"
        f"Услуга: {data['service_name']}\n"
        f"Дата: {format_date(data['appointment_time'])}\n"
        f"Время: {format_time(data['appointment_time'])}\n"
        f"Имя: {data['client_name']}\n"
        f"Телефон: {data['client_phone']}\n\n"
        f"Всё верно?"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Да", callback_data="confirm_booking"),
            InlineKeyboardButton("❌ Нет", callback_data="book_service")
        ]
    ]
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    return CONFIRM_APPOINTMENT

async def confirm_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение записи"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if user_id not in appointment_data:
        await query.message.edit_text(
            "Произошла ошибка. Начните запись заново.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« В начало", callback_data="book_service")
            ]])
        )
        return ConversationHandler.END
    
    db = SessionLocal()
    try:
        data = appointment_data[user_id]
        appointment_in = AppointmentCreate(
            client_telegram_id=str(user_id),
            client_name=data['client_name'],
            client_phone=data['client_phone'],
            service_id=data['service_id'],
            admin_id=data['admin_id'],
            appointment_time=data['appointment_time']
        )
        
        try:
            appointment = crud_appointment.create_with_validation(db, obj_in=appointment_in)
            
            await query.message.edit_text(
                f"✅ Запись успешно создана!\n\n"
                f"Услуга: {data['service_name']}\n"
                f"Дата: {format_date(data['appointment_time'])}\n"
                f"Время: {format_time(data['appointment_time'])}\n"
                f"Имя: {data['client_name']}\n"
                f"Телефон: {data['client_phone']}\n\n"
                f"Ждём вас!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« В главное меню", callback_data="start")
                ]])
            )
        except ValueError as e:
            await query.message.edit_text(
                f"❌ Ошибка при создании записи: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Попробовать снова", callback_data="book_service")
                ]])
            )
    finally:
        db.close()
        if user_id in appointment_data:
            del appointment_data[user_id]
    
    return ConversationHandler.END

async def cancel_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена процесса записи"""
    user_id = update.effective_user.id
    if user_id in appointment_data:
        del appointment_data[user_id]
    
    if update.callback_query:
        await update.callback_query.message.edit_text(
            "Запись отменена.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« В главное меню", callback_data="start")
            ]])
        )
    else:
        await update.message.reply_text(
            "Запись отменена.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« В главное меню", callback_data="start")
            ]])
        )
    
    return ConversationHandler.END