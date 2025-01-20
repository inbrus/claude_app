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
        # Получаем активные и прошлые записи
        current_appointments = crud_appointment.get_by_client(
            db,
            client_telegram_id=str(user.id),
            include_past=False
        )
        
        past_appointments = crud_appointment.get_by_client(
            db,
            client_telegram_id=str(user.id),
            include_past=True
        )
        past_appointments = [apt for apt in past_appointments if apt.appointment_time < datetime.now()]
        
        if not current_appointments and not past_appointments:
            keyboard = [
                [InlineKeyboardButton("📝 Записаться", callback_data="select_service")],
                [InlineKeyboardButton("« Назад", callback_data="client_menu")]
            ]
            await update.callback_query.message.edit_text(
                "У вас пока нет записей.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        text = "Ваши записи:\n\n"
        keyboard = []
        
        if current_appointments:
            text += "📅 Предстоящие записи:\n\n"
            for apt in sorted(current_appointments, key=lambda x: x.appointment_time):
                text += (
                    f"Дата: {apt.appointment_time.strftime('%d.%m.%Y')}\n"
                    f"Время: {apt.appointment_time.strftime('%H:%M')}\n"
                    f"Услуга: {apt.service.name}\n"
                    f"Статус: {apt.status}\n\n"
                )
                
                # Добавляем кнопки управления для каждой записи
                if apt.status != "cancelled":
                    keyboard.append([
                        InlineKeyboardButton(
                            f"⚙️ {apt.appointment_time.strftime('%d.%m.%Y %H:%M')}",
                            callback_data=f"manage_client_appointment_{apt.id}"
                        )
                    ])
        
        if past_appointments:
            text += "\n📅 Прошлые записи:\n\n"
            for apt in sorted(past_appointments, key=lambda x: x.appointment_time, reverse=True)[:5]:
                text += (
                    f"Дата: {apt.appointment_time.strftime('%d.%m.%Y')}\n"
                    f"Время: {apt.appointment_time.strftime('%H:%M')}\n"
                    f"Услуга: {apt.service.name}\n"
                    f"Статус: {apt.status}\n\n"
                )
        
        keyboard.extend([
            [InlineKeyboardButton("📝 Записаться", callback_data="select_service")],
            [InlineKeyboardButton("« Назад", callback_data="client_menu")]
        ])
        
        await update.callback_query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    finally:
        db.close()

async def manage_client_appointment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Управление конкретной записью клиентом"""
    query = update.callback_query
    appointment_id = int(query.data.split('_')[-1])
    
    db = SessionLocal()
    try:
        appointment = crud_appointment.get(db, id=appointment_id)
        if not appointment or str(query.from_user.id) != appointment.client_telegram_id:
            await query.message.edit_text(
                "Запись не найдена или у вас нет прав для её управления.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« К моим записям", callback_data="my_appointments")
                ]])
            )
            return
        
        text = (
            f"Управление записью:\n\n"
            f"Услуга: {appointment.service.name}\n"
            f"Дата: {appointment.appointment_time.strftime('%d.%m.%Y')}\n"
            f"Время: {appointment.appointment_time.strftime('%H:%M')}\n"
            f"Статус: {appointment.status}\n"
        )
        
        keyboard = []
        if appointment.status != "cancelled":
            keyboard.extend([
                [InlineKeyboardButton("🕒 Перенести", callback_data=f"reschedule_appointment_{appointment_id}")],
                [InlineKeyboardButton("❌ Отменить", callback_data=f"client_cancel_appointment_{appointment_id}")]
            ])
        
        keyboard.append([InlineKeyboardButton("« К моим записям", callback_data="my_appointments")])
        
        await query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    finally:
        db.close()

async def client_cancel_appointment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена записи клиентом"""
    query = update.callback_query
    appointment_id = int(query.data.split('_')[-1])
    
    db = SessionLocal()
    try:
        appointment = crud_appointment.get(db, id=appointment_id)
        if not appointment or str(query.from_user.id) != appointment.client_telegram_id:
            await query.message.edit_text(
                "Запись не найдена или у вас нет прав для её управления.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« К моим записям", callback_data="my_appointments")
                ]])
            )
            return
        
        # Запрос подтверждения
        text = (
            f"Вы действительно хотите отменить запись?\n\n"
            f"Услуга: {appointment.service.name}\n"
            f"Дата: {appointment.appointment_time.strftime('%d.%m.%Y')}\n"
            f"Время: {appointment.appointment_time.strftime('%H:%M')}"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Да", callback_data=f"confirm_client_cancel_{appointment_id}"),
                InlineKeyboardButton("❌ Нет", callback_data=f"manage_client_appointment_{appointment_id}")
            ]
        ]
        
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        db.close()

async def confirm_client_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение отмены записи клиентом"""
    query = update.callback_query
    appointment_id = int(query.data.split('_')[-1])
    
    db = SessionLocal()
    try:
        appointment = crud_appointment.update_status(
            db,
            appointment_id=appointment_id,
            new_status="cancelled"
        )
        
        if appointment:
            # Отправляем уведомление администратору
            await notify_admin_appointment_cancelled(context.bot, appointment.admin_id, appointment.id)
            
            await query.message.edit_text(
                "✅ Запись успешно отменена!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« К моим записям", callback_data="my_appointments")
                ]])
            )
        else:
            await query.message.edit_text(
                "Произошла ошибка при отмене записи.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« К моим записям", callback_data="my_appointments")
                ]])
            )
    finally:
        db.close()

async def start_reschedule_appointment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса переноса записи"""
    query = update.callback_query
    appointment_id = int(query.data.split('_')[-1])
    
    db = SessionLocal()
    try:
        appointment = crud_appointment.get(db, id=appointment_id)
        if not appointment or str(query.from_user.id) != appointment.client_telegram_id:
            await query.message.edit_text(
                "Запись не найдена или у вас нет прав для её управления.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« К моим записям", callback_data="my_appointments")
                ]])
            )
            return
        
        # Получаем доступные слоты для этой услуги
        today = datetime.now().date()
        keyboard = []
        for i in range(14):  # Показываем записи на 2 недели вперед
            date = today + timedelta(days=i)
            keyboard.append([
                InlineKeyboardButton(
                    date.strftime('%d.%m.%Y'),
                    callback_data=f"reschedule_date_{appointment_id}_{date.isoformat()}"
                )
            ])
        keyboard.append([
            InlineKeyboardButton("« Отмена", callback_data=f"manage_client_appointment_{appointment_id}")
        ])
        
        await query.message.edit_text(
            f"Текущее время записи: {appointment.appointment_time.strftime('%d.%m.%Y %H:%M')}\n"
            f"Выберите новую дату:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    finally:
        db.close()

async def select_reschedule_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор новой даты для переноса записи"""
    query = update.callback_query
    appointment_id, date_str = query.data.split('_')[-2:]
    appointment_id = int(appointment_id)
    selected_date = datetime.fromisoformat(date_str)
    
    db = SessionLocal()
    try:
        appointment = crud_appointment.get(db, id=appointment_id)
        if not appointment or str(query.from_user.id) != appointment.client_telegram_id:
            await query.message.edit_text(
                "Запись не найдена или у вас нет прав для её управления.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« К моим записям", callback_data="my_appointments")
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
                    InlineKeyboardButton("« К выбору даты", callback_data=f"reschedule_appointment_{appointment_id}")
                ]])
            )
            return
        
        # Показываем доступные слоты
        keyboard = []
        for slot in available_slots:
            keyboard.append([
                InlineKeyboardButton(
                    slot.strftime('%H:%M'),
                    callback_data=f"confirm_reschedule_{appointment_id}_{slot.isoformat()}"
                )
            ])
        keyboard.append([
            InlineKeyboardButton("« К выбору даты", callback_data=f"reschedule_appointment_{appointment_id}")
        ])
        
        await query.message.edit_text(
            f"Выбрана дата: {selected_date.strftime('%d.%m.%Y')}\n"
            f"Выберите новое время:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    finally:
        db.close()

async def confirm_reschedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение переноса записи"""
    query = update.callback_query
    appointment_id, time_str = query.data.split('_')[-2:]
    appointment_id = int(appointment_id)
    new_time = datetime.fromisoformat(time_str)
    
    db = SessionLocal()
    try:
        appointment = crud_appointment.get(db, id=appointment_id)
        if not appointment or str(query.from_user.id) != appointment.client_telegram_id:
            await query.message.edit_text(
                "Запись не найдена или у вас нет прав для её управления.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« К моим записям", callback_data="my_appointments")
                ]])
            )
            return
        
        # Обновляем время записи
        updated = crud_appointment.update(
            db,
            db_obj=appointment,
            obj_in=AppointmentUpdate(
                appointment_time=new_time,
                status="pending"  # Сбрасываем статус на "ожидает подтверждения"
            )
        )
        
        if updated:
            # Отправляем уведомление администратору
            await notify_admin_new_appointment(context.bot, updated.admin_id, updated.id)
            
            await query.message.edit_text(
                f"✅ Запись успешно перенесена на {new_time.strftime('%d.%m.%Y %H:%M')}!\n"
                f"Ожидайте подтверждения администратора.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« К моим записям", callback_data="my_appointments")
                ]])
            )
        else:
            await query.message.edit_text(
                "Произошла ошибка при переносе записи.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« К моим записям", callback_data="my_appointments")
                ]])
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