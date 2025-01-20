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
        
        # Получаем фильтры из контекста, если они есть
        filters = context.user_data.get('appointment_filters', {})
        date_range = filters.get('date_range', 'today_tomorrow')  # today_tomorrow, week, month
        status = filters.get('status', None)  # pending, confirmed, cancelled
        
        if date_range == 'week':
            end_date = today + timedelta(days=7)
        elif date_range == 'month':
            end_date = today + timedelta(days=30)
        else:  # today_tomorrow
            end_date = tomorrow + timedelta(days=1)
        
        appointments = crud_appointment.get_by_date_range(
            db,
            start_date=today,
            end_date=end_date,
            admin_id=admin_id,
            status=status
        )
        
        # Добавляем кнопки управления
        keyboard = [
            [InlineKeyboardButton("➕ Создать запись", callback_data="create_appointment")],
            [
                InlineKeyboardButton("📅 Сегодня-завтра", callback_data="filter_date_today_tomorrow"),
                InlineKeyboardButton("📅 Неделя", callback_data="filter_date_week")
            ],
            [
                InlineKeyboardButton("⏳ Ожидают", callback_data="filter_status_pending"),
                InlineKeyboardButton("✅ Подтверждены", callback_data="filter_status_confirmed"),
                InlineKeyboardButton("❌ Отменены", callback_data="filter_status_cancelled")
            ],
            [InlineKeyboardButton("🔄 Сбросить фильтры", callback_data="filter_reset")],
            [InlineKeyboardButton("« Назад", callback_data="admin_menu")]
        ]
        
        if not appointments:
            await update.callback_query.message.edit_text(
                "Записей не найдено.",
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
        
        # Добавляем кнопки для каждой записи
        for day, day_appointments in appointments_by_day.items():
            for apt in day_appointments:
                keyboard.insert(-1, [
                    InlineKeyboardButton(
                        f"⚙️ {format_time(apt.appointment_time)} - {apt.client_name}",
                        callback_data=f"manage_appointment_{apt.id}"
                    )
                ])
        
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

async def manage_appointment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Управление конкретной записью"""
    query = update.callback_query
    appointment_id = int(query.data.split('_')[-1])
    
    db = SessionLocal()
    try:
        appointment = crud_appointment.get(db, id=appointment_id)
        if not appointment:
            await query.message.edit_text(
                "Запись не найдена.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« К списку записей", callback_data="view_appointments")
                ]])
            )
            return
        
        text = (
            f"Управление записью:\n\n"
            f"Клиент: {appointment.client_name}\n"
            f"Телефон: {appointment.client_phone}\n"
            f"Услуга: {appointment.service.name}\n"
            f"Дата: {format_date(appointment.appointment_time)}\n"
            f"Время: {format_time(appointment.appointment_time)}\n"
            f"Статус: {appointment.status}\n"
        )
        
        keyboard = [
            [InlineKeyboardButton("✏️ Изменить время", callback_data=f"edit_appointment_time_{appointment_id}")],
            [InlineKeyboardButton("✏️ Изменить услугу", callback_data=f"edit_appointment_service_{appointment_id}")],
            [
                InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_appointment_{appointment_id}"),
                InlineKeyboardButton("❌ Отменить", callback_data=f"cancel_appointment_{appointment_id}")
            ],
            [InlineKeyboardButton("« К списку записей", callback_data="view_appointments")]
        ]
        
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        db.close()

async def update_appointment_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обновление статуса записи"""
    query = update.callback_query
    action, appointment_id = query.data.split('_')[-2:]
    appointment_id = int(appointment_id)
    new_status = "confirmed" if action == "confirm" else "cancelled"
    
    db = SessionLocal()
    try:
        appointment = crud_appointment.update_status(
            db,
            appointment_id=appointment_id,
            new_status=new_status
        )
        
        if appointment:
            status_text = "подтверждена" if new_status == "confirmed" else "отменена"
            await query.message.edit_text(
                f"Запись успешно {status_text}!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« К списку записей", callback_data="view_appointments")
                ]])
            )
        else:
            await query.message.edit_text(
                "Ошибка при обновлении статуса записи.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« К списку записей", callback_data="view_appointments")
                ]])
            )
    finally:
        db.close()

async def edit_appointment_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало редактирования времени записи"""
    query = update.callback_query
    appointment_id = int(query.data.split('_')[-1])
    
    db = SessionLocal()
    try:
        appointment = crud_appointment.get(db, id=appointment_id)
        if not appointment:
            await query.message.edit_text(
                "Запись не найдена.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« К списку записей", callback_data="view_appointments")
                ]])
            )
            return
        
        # Показываем календарь на ближайшие дни
        today = datetime.now().date()
        keyboard = []
        for i in range(14):
            date = today + timedelta(days=i)
            keyboard.append([
                InlineKeyboardButton(
                    format_date(date),
                    callback_data=f"change_date_{appointment_id}_{date.isoformat()}"
                )
            ])
        keyboard.append([
            InlineKeyboardButton("« Назад", callback_data=f"manage_appointment_{appointment_id}")
        ])
        
        await query.message.edit_text(
            f"Текущее время записи: {format_date(appointment.appointment_time)} {format_time(appointment.appointment_time)}\n"
            f"Выберите новую дату:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    finally:
        db.close()

async def change_appointment_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор новой даты для записи"""
    query = update.callback_query
    appointment_id, date_str = query.data.split('_')[-2:]
    appointment_id = int(appointment_id)
    selected_date = datetime.fromisoformat(date_str)
    
    db = SessionLocal()
    try:
        appointment = crud_appointment.get(db, id=appointment_id)
        if not appointment:
            await query.message.edit_text(
                "Запись не найдена.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« К списку записей", callback_data="view_appointments")
                ]])
            )
            return
        
        # Получаем доступные слоты
        available_slots = crud_appointment.get_available_slots(
            db,
            admin_id=appointment.admin_id,
            date=selected_date,
            service_duration=appointment.service.duration
        )
        
        if not available_slots:
            await query.message.edit_text(
                "На эту дату нет свободных окон.\n"
                "Пожалуйста, выберите другую дату:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« К выбору даты", callback_data=f"edit_appointment_time_{appointment_id}")
                ]])
            )
            return
        
        # Показываем доступные слоты
        keyboard = []
        for slot in available_slots:
            keyboard.append([
                InlineKeyboardButton(
                    format_time(slot),
                    callback_data=f"update_time_{appointment_id}_{slot.isoformat()}"
                )
            ])
        keyboard.append([
            InlineKeyboardButton("« К выбору даты", callback_data=f"edit_appointment_time_{appointment_id}")
        ])
        
        await query.message.edit_text(
            f"Выбрана дата: {format_date(selected_date)}\n"
            f"Выберите новое время:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    finally:
        db.close()

async def update_appointment_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обновление времени записи"""
    query = update.callback_query
    appointment_id, time_str = query.data.split('_')[-2:]
    appointment_id = int(appointment_id)
    new_time = datetime.fromisoformat(time_str)
    
    db = SessionLocal()
    try:
        appointment = crud_appointment.get(db, id=appointment_id)
        if not appointment:
            await query.message.edit_text(
                "Запись не найдена.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« К списку записей", callback_data="view_appointments")
                ]])
            )
            return
        
        # Обновляем время записи
        updated = crud_appointment.update(
            db,
            db_obj=appointment,
            obj_in=AppointmentUpdate(appointment_time=new_time)
        )
        
        await query.message.edit_text(
            f"✅ Время записи успешно изменено на {format_date(new_time)} {format_time(new_time)}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« К записи", callback_data=f"manage_appointment_{appointment_id}")
            ]])
        )
    finally:
        db.close()

async def edit_appointment_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Редактирование услуги"""
    query = update.callback_query
    appointment_id = int(query.data.split('_')[-1])
    
    db = SessionLocal()
    try:
        appointment = crud_appointment.get(db, id=appointment_id)
        if not appointment:
            await query.message.edit_text(
                "Запись не найдена.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« К списку записей", callback_data="view_appointments")
                ]])
            )
            return
        
        services = crud_service.get_multi(db)
        active_services = [s for s in services if s.is_active]
        
        if not active_services:
            await query.message.edit_text(
                "Нет доступных услуг.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« К записи", callback_data=f"manage_appointment_{appointment_id}")
                ]])
            )
            return
        
        keyboard = []
        for service in active_services:
            keyboard.append([
                InlineKeyboardButton(
                    f"{service.name} - {service.price}₽",
                    callback_data=f"update_service_{appointment_id}_{service.id}"
                )
            ])
        keyboard.append([
            InlineKeyboardButton("« Назад", callback_data=f"manage_appointment_{appointment_id}")
        ])
        
        await query.message.edit_text(
            f"Текущая услуга: {appointment.service.name}\n"
            f"Выберите новую услугу:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    finally:
        db.close()

async def update_appointment_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обновление услуги в записи"""
    query = update.callback_query
    appointment_id, service_id = map(int, query.data.split('_')[-2:])
    
    db = SessionLocal()
    try:
        appointment = crud_appointment.get(db, id=appointment_id)
        if not appointment:
            await query.message.edit_text(
                "Запись не найдена.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« К списку записей", callback_data="view_appointments")
                ]])
            )
            return
        
        service = crud_service.get(db, id=service_id)
        if not service or not service.is_active:
            await query.message.edit_text(
                "Услуга не найдена или неактивна.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« К записи", callback_data=f"manage_appointment_{appointment_id}")
                ]])
            )
            return
        
        # Проверяем, доступно ли текущее время для новой услуги
        available_slots = crud_appointment.get_available_slots(
            db,
            admin_id=appointment.admin_id,
            date=appointment.appointment_time,
            service_duration=service.duration
        )
        
        if appointment.appointment_time not in available_slots:
            await query.message.edit_text(
                "Невозможно изменить услугу: текущее время будет недоступно для новой услуги.\n"
                "Пожалуйста, сначала измените время записи.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« К записи", callback_data=f"manage_appointment_{appointment_id}")
                ]])
            )
            return
        
        # Обновляем услугу
        updated = crud_appointment.update(
            db,
            db_obj=appointment,
            obj_in=AppointmentUpdate(service_id=service_id)
        )
        
        await query.message.edit_text(
            f"✅ Услуга успешно изменена на {service.name}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« К записи", callback_data=f"manage_appointment_{appointment_id}")
            ]])
        )
    finally:
        db.close()

async def update_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обновление фильтров для просмотра записей"""
    query = update.callback_query
    filter_type, filter_value = query.data.split('_')[1:3]
    
    if 'appointment_filters' not in context.user_data:
        context.user_data['appointment_filters'] = {}
    
    if filter_type == 'date':
        context.user_data['appointment_filters']['date_range'] = filter_value
        context.user_data['appointment_filters'].pop('status', None)  # Сбрасываем фильтр статуса
    elif filter_type == 'status':
        context.user_data['appointment_filters']['status'] = filter_value
        context.user_data['appointment_filters'].pop('date_range', None)  # Сбрасываем фильтр даты
    elif filter_type == 'reset':
        context.user_data['appointment_filters'] = {}
    
    await view_appointments(update, context)

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