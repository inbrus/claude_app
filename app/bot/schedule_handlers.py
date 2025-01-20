from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from datetime import datetime, time, timedelta
from app.crud.crud_schedule import crud_schedule, crud_time_slot
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate, TimeSlotCreate
from app.db.session import SessionLocal

# Состояния диалога
(
    ENTER_START_TIME,
    ENTER_END_TIME,
    ENTER_BREAK_START,
    ENTER_BREAK_END,
    CONFIRM_SCHEDULE,
) = range(5)

# Временное хранилище данных
schedule_data = {}

# Дни недели
WEEKDAYS = {
    0: "Понедельник",
    1: "Вторник",
    2: "Среда",
    3: "Четверг",
    4: "Пятница",
    5: "Суббота",
    6: "Воскресенье"
}

def format_time(t: time) -> str:
    """Форматирование времени"""
    return t.strftime("%H:%M")

async def manage_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Управление расписанием"""
    db = SessionLocal()
    try:
        admin_id = context.user_data.get('admin_id')
        schedule = crud_schedule.get_by_admin(db, admin_id=admin_id)
        
        keyboard = []
        for day in range(7):
            day_schedule = next((s for s in schedule if s.day_of_week == day), None)
            status = "✅" if day_schedule and day_schedule.is_working else "❌"
            text = f"{status} {WEEKDAYS[day]}"
            if day_schedule:
                text += f" ({format_time(day_schedule.start_time)}-{format_time(day_schedule.end_time)})"
            keyboard.append([
                InlineKeyboardButton(text, callback_data=f"edit_day_{day}")
            ])
        
        keyboard.append([InlineKeyboardButton("📅 Особые дни", callback_data="special_days")])
        keyboard.append([InlineKeyboardButton("« Назад", callback_data="admin_menu")])
        
        await update.callback_query.message.edit_text(
            "Управление расписанием:\n"
            "✅ - рабочий день\n"
            "❌ - выходной день\n"
            "Выберите день для редактирования:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    finally:
        db.close()

async def edit_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Редактирование дня"""
    query = update.callback_query
    day = int(query.data.split('_')[-1])
    db = SessionLocal()
    
    try:
        admin_id = context.user_data.get('admin_id')
        schedule = crud_schedule.get_by_day(db, admin_id=admin_id, day_of_week=day)
        
        text = f"День: {WEEKDAYS[day]}\n"
        if schedule:
            status = "рабочий" if schedule.is_working else "выходной"
            text += (
                f"Статус: {status}\n"
                f"Начало работы: {format_time(schedule.start_time)}\n"
                f"Конец работы: {format_time(schedule.end_time)}\n"
            )
            if schedule.break_start and schedule.break_end:
                text += (
                    f"Перерыв: {format_time(schedule.break_start)} - "
                    f"{format_time(schedule.break_end)}\n"
                )
        else:
            text += "Расписание не настроено\n"
        
        keyboard = []
        if schedule and schedule.is_working:
            keyboard.extend([
                [InlineKeyboardButton("⏰ Изменить время работы", callback_data=f"change_time_{day}")],
                [InlineKeyboardButton("🕐 Изменить перерыв", callback_data=f"change_break_{day}")],
                [InlineKeyboardButton("❌ Сделать выходным", callback_data=f"toggle_day_{day}")]
            ])
        else:
            keyboard.append([
                InlineKeyboardButton("✅ Сделать рабочим", callback_data=f"set_working_{day}")
            ])
        
        keyboard.append([InlineKeyboardButton("« Назад", callback_data="manage_schedule")])
        
        await query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    finally:
        db.close()

async def start_set_working(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало настройки рабочего дня"""
    query = update.callback_query
    day = int(query.data.split('_')[-1])
    user_id = query.from_user.id
    
    schedule_data[user_id] = {
        'day': day,
        'is_working': True
    }
    
    await query.message.edit_text(
        f"Настройка рабочего дня ({WEEKDAYS[day]})\n\n"
        "Введите время начала работы в формате ЧЧ:ММ (например, 09:00):",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("« Отмена", callback_data=f"edit_day_{day}")
        ]])
    )
    return ENTER_START_TIME

async def process_start_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода времени начала работы"""
    user_id = update.message.from_user.id
    time_str = update.message.text
    
    try:
        hours, minutes = map(int, time_str.split(':'))
        start_time = time(hours, minutes)
    except (ValueError, TypeError):
        await update.message.reply_text(
            "Неверный формат времени. Пожалуйста, введите время в формате ЧЧ:ММ:"
        )
        return ENTER_START_TIME
    
    schedule_data[user_id]['start_time'] = start_time
    day = schedule_data[user_id]['day']
    
    await update.message.reply_text(
        f"Введите время окончания работы в формате ЧЧ:ММ:",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("« Отмена", callback_data=f"edit_day_{day}")
        ]])
    )
    return ENTER_END_TIME

async def process_end_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода времени окончания работы"""
    user_id = update.message.from_user.id
    time_str = update.message.text
    
    try:
        hours, minutes = map(int, time_str.split(':'))
        end_time = time(hours, minutes)
        if end_time <= schedule_data[user_id]['start_time']:
            raise ValueError("Время окончания должно быть позже времени начала")
    except (ValueError, TypeError) as e:
        await update.message.reply_text(
            f"Ошибка: {str(e)}. Пожалуйста, введите корректное время:"
        )
        return ENTER_END_TIME
    
    schedule_data[user_id]['end_time'] = end_time
    day = schedule_data[user_id]['day']
    
    # Спрашиваем про перерыв
    keyboard = [
        [
            InlineKeyboardButton("✅ Да", callback_data="set_break"),
            InlineKeyboardButton("❌ Нет", callback_data="skip_break")
        ]
    ]
    await update.message.reply_text(
        "Хотите добавить перерыв?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ENTER_BREAK_START

async def process_break_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода времени начала перерыва"""
    user_id = update.message.from_user.id
    time_str = update.message.text
    
    try:
        hours, minutes = map(int, time_str.split(':'))
        break_start = time(hours, minutes)
        if not (schedule_data[user_id]['start_time'] < break_start < schedule_data[user_id]['end_time']):
            raise ValueError("Перерыв должен быть в рабочее время")
    except (ValueError, TypeError) as e:
        await update.message.reply_text(
            f"Ошибка: {str(e)}. Пожалуйста, введите корректное время:"
        )
        return ENTER_BREAK_START
    
    schedule_data[user_id]['break_start'] = break_start
    day = schedule_data[user_id]['day']
    
    await update.message.reply_text(
        f"Введите время окончания перерыва в формате ЧЧ:ММ:",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("« Отмена", callback_data=f"edit_day_{day}")
        ]])
    )
    return ENTER_BREAK_END

async def process_break_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода времени окончания перерыва"""
    user_id = update.message.from_user.id
    time_str = update.message.text
    
    try:
        hours, minutes = map(int, time_str.split(':'))
        break_end = time(hours, minutes)
        if not (schedule_data[user_id]['break_start'] < break_end < schedule_data[user_id]['end_time']):
            raise ValueError("Время окончания перерыва должно быть после его начала и до конца рабочего дня")
    except (ValueError, TypeError) as e:
        await update.message.reply_text(
            f"Ошибка: {str(e)}. Пожалуйста, введите корректное время:"
        )
        return ENTER_BREAK_END
    
    schedule_data[user_id]['break_end'] = break_end
    
    # Показываем сводку для подтверждения
    schedule = schedule_data[user_id]
    text = (
        f"Проверьте настройки расписания:\n\n"
        f"День: {WEEKDAYS[schedule['day']]}\n"
        f"Начало работы: {format_time(schedule['start_time'])}\n"
        f"Конец работы: {format_time(schedule['end_time'])}\n"
    )
    if 'break_start' in schedule and 'break_end' in schedule:
        text += (
            f"Перерыв: {format_time(schedule['break_start'])} - "
            f"{format_time(schedule['break_end'])}\n"
        )
    text += "\nВсё верно?"
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Да", callback_data="confirm_schedule"),
            InlineKeyboardButton("❌ Нет", callback_data=f"edit_day_{schedule['day']}")
        ]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    return CONFIRM_SCHEDULE

async def confirm_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение и сохранение расписания"""
    query = update.callback_query
    user_id = query.from_user.id
    db = SessionLocal()
    
    try:
        schedule = schedule_data[user_id]
        admin_id = context.user_data.get('admin_id')
        
        # Создаем или обновляем расписание
        existing_schedule = crud_schedule.get_by_day(
            db, admin_id=admin_id, day_of_week=schedule['day']
        )
        
        schedule_data = {
            'admin_id': admin_id,
            'day_of_week': schedule['day'],
            'start_time': schedule['start_time'],
            'end_time': schedule['end_time'],
            'is_working': True,
            'break_start': schedule.get('break_start'),
            'break_end': schedule.get('break_end')
        }
        
        if existing_schedule:
            updated_schedule = crud_schedule.update(
                db,
                db_obj=existing_schedule,
                obj_in=ScheduleUpdate(**schedule_data)
            )
        else:
            updated_schedule = crud_schedule.create(
                db,
                obj_in=ScheduleCreate(**schedule_data)
            )
        
        await query.message.edit_text(
            f"✅ Расписание на {WEEKDAYS[schedule['day']]} успешно сохранено!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« К расписанию", callback_data="manage_schedule")
            ]])
        )
    except Exception as e:
        await query.message.edit_text(
            f"❌ Ошибка при сохранении расписания: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« К расписанию", callback_data="manage_schedule")
            ]])
        )
    finally:
        db.close()
        if user_id in schedule_data:
            del schedule_data[user_id]
    
    return ConversationHandler.END

async def toggle_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Включение/отключение рабочего дня"""
    query = update.callback_query
    day = int(query.data.split('_')[-1])
    db = SessionLocal()
    
    try:
        admin_id = context.user_data.get('admin_id')
        schedule = crud_schedule.get_by_day(db, admin_id=admin_id, day_of_week=day)
        
        if schedule:
            # Инвертируем статус дня
            updated_schedule = crud_schedule.update(
                db,
                db_obj=schedule,
                obj_in=ScheduleUpdate(is_working=not schedule.is_working)
            )
            status = "рабочим" if updated_schedule.is_working else "выходным"
            await query.message.edit_text(
                f"✅ {WEEKDAYS[day]} успешно сделан {status}!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« К расписанию", callback_data="manage_schedule")
                ]])
            )
        else:
            await query.message.edit_text(
                "❌ Сначала настройте расписание на этот день",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« К расписанию", callback_data="manage_schedule")
                ]])
            )
    finally:
        db.close()