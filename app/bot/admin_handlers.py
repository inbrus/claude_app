from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from datetime import datetime, timedelta
import re
import logging
from app.crud.crud_service import crud_service
from app.crud.crud_appointment import crud_appointment
from app.schemas.service import ServiceCreate, ServiceUpdate
from app.db.session import SessionLocal
from app.bot.notifications import notify_admin_new_appointment

logger = logging.getLogger(__name__)

# Состояния диалога
(
    ENTER_SERVICE_NAME,
    ENTER_SERVICE_DESCRIPTION,
    ENTER_SERVICE_PRICE,
    ENTER_SERVICE_DURATION,
    CONFIRM_SERVICE,
    EDIT_SERVICE_FIELD,
) = range(6)

# Временное хранилище данных
service_data = {}

async def manage_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Управление услугами"""
    debug_file = "debug.log"
    with open(debug_file, "a") as f:
        f.write("\n=== manage_services called ===\n")
        
        if not update.callback_query:
            f.write("No callback query\n")
            return
            
        f.write("Getting services from database\n")
        db = SessionLocal()
        try:
            try:
                services = crud_service.get_multi(db)
                f.write(f"Got services: {services}\n")
                
                text = "Управление услугами:\n\n"
                if services:
                    for service in services:
                        f.write(f"Processing service: {service}\n")
                        status = "✅" if service.is_active else "❌"
                        text += f"{status} {service.name} - {service.price}₽\n"
                else:
                    text += "Услуги не добавлены."
                    f.write("No services found\n")
                
                keyboard = [
                    [InlineKeyboardButton("➕ Добавить услугу", callback_data="add_service")],
                    [InlineKeyboardButton("« Назад", callback_data="admin_menu")]
                ]
                
                # Добавляем кнопки для каждой услуги
                if services:
                    for service in services:
                        keyboard.insert(-1, [
                            InlineKeyboardButton(
                                f"⚙️ {service.name}",
                                callback_data=f"edit_service_{service.id}"
                            )
                        ])
                
                f.write(f"Final text: {text}\n")
                f.write(f"Keyboard: {keyboard}\n")
                
                await update.callback_query.message.edit_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                f.write("Message sent successfully\n")
                
            except Exception as e:
                f.write(f"Error in manage_services: {str(e)}\n")
                f.write(f"Error type: {type(e)}\n")
                f.write(f"Error args: {e.args}\n")
                import traceback
                f.write(f"Traceback: {traceback.format_exc()}\n")
                await update.callback_query.message.edit_text(
                    "Произошла ошибка при получении списка услуг.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Назад", callback_data="admin_menu")
                    ]])
                )
        finally:
            db.close()
            f.write("Database session closed\n")

async def edit_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню редактирования услуги"""
    query = update.callback_query
    service_id = int(query.data.split('_')[-1])
    db = SessionLocal()
    
    try:
        service = crud_service.get(db, id=service_id)
        if not service:
            await query.message.edit_text(
                "❌ Услуга не найдена",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Назад", callback_data="manage_services")
                ]])
            )
            return
        
        status = "включена" if service.is_active else "отключена"
        text = (
            f"Услуга: {service.name}\n"
            f"Описание: {service.description or 'Нет'}\n"
            f"Стоимость: {service.price}₽\n"
            f"Длительность: {service.duration} минут\n"
            f"Статус: {status}\n\n"
            f"Выберите действие:"
        )
        
        keyboard = [
            [InlineKeyboardButton("✏️ Изменить название", callback_data=f"edit_name_{service_id}")],
            [InlineKeyboardButton("✏️ Изменить описание", callback_data=f"edit_description_{service_id}")],
            [InlineKeyboardButton("✏️ Изменить стоимость", callback_data=f"edit_price_{service_id}")],
            [InlineKeyboardButton("✏️ Изменить длительность", callback_data=f"edit_duration_{service_id}")],
            [InlineKeyboardButton(
                "❌ Отключить" if service.is_active else "✅ Включить",
                callback_data=f"toggle_service_{service_id}"
            )],
            [InlineKeyboardButton("🗑 Удалить услугу", callback_data=f"delete_service_{service_id}")],
            [InlineKeyboardButton("« Назад", callback_data="manage_services")]
        ]
        
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        db.close()

async def toggle_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Включение/отключение услуги"""
    query = update.callback_query
    service_id = int(query.data.split('_')[-1])
    db = SessionLocal()
    
    try:
        service = crud_service.get(db, id=service_id)
        if not service:
            await query.message.edit_text(
                "❌ Услуга не найдена",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Назад", callback_data="manage_services")
                ]])
            )
            return
        
        # Обновляем статус услуги
        service_update = ServiceUpdate(is_active=not service.is_active)
        updated_service = crud_service.update(db, db_obj=service, obj_in=service_update)
        
        status = "включена" if updated_service.is_active else "отключена"
        await query.message.edit_text(
            f"✅ Услуга {updated_service.name} {status}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« К списку услуг", callback_data="manage_services")
            ]])
        )
    finally:
        db.close()

async def delete_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаление услуги"""
    query = update.callback_query
    service_id = int(query.data.split('_')[-1])
    db = SessionLocal()
    
    try:
        service = crud_service.get(db, id=service_id)
        if not service:
            await query.message.edit_text(
                "❌ Услуга не найдена",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Назад", callback_data="manage_services")
                ]])
            )
            return
        
        # Запрос подтверждения
        text = (
            f"❗️ Вы действительно хотите удалить услугу?\n\n"
            f"Название: {service.name}\n"
            f"Стоимость: {service.price}₽\n\n"
            f"Это действие нельзя отменить!"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_delete_{service_id}"),
                InlineKeyboardButton("❌ Нет, отмена", callback_data=f"edit_service_{service_id}")
            ]
        ]
        
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        db.close()

async def start_edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало редактирования поля услуги"""
    query = update.callback_query
    field_type, service_id = query.data.split('_')[1:3]
    service_id = int(service_id)
    
    db = SessionLocal()
    try:
        service = crud_service.get(db, id=service_id)
        if not service:
            await query.message.edit_text(
                "❌ Услуга не найдена",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Назад", callback_data="manage_services")
                ]])
            )
            return
        
        field_names = {
            'name': 'название',
            'description': 'описание',
            'price': 'стоимость',
            'duration': 'длительность'
        }
        
        current_value = getattr(service, field_type)
        text = (
            f"Текущее {field_names[field_type]}: {current_value}\n"
            f"Введите новое значение:"
        )
        
        # Сохраняем данные в контексте
        context.user_data['edit_service'] = {
            'id': service_id,
            'field': field_type
        }
        
        await query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Отмена", callback_data=f"edit_service_{service_id}")
            ]])
        )
        return EDIT_SERVICE_FIELD
    finally:
        db.close()

async def process_edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода нового значения поля"""
    if 'edit_service' not in context.user_data:
        await update.message.reply_text(
            "❌ Ошибка: данные редактирования не найдены",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« К списку услуг", callback_data="manage_services")
            ]])
        )
        return ConversationHandler.END
    
    service_id = context.user_data['edit_service']['id']
    field_type = context.user_data['edit_service']['field']
    new_value = update.message.text
    
    db = SessionLocal()
    try:
        service = crud_service.get(db, id=service_id)
        if not service:
            await update.message.reply_text(
                "❌ Услуга не найдена",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« К списку услуг", callback_data="manage_services")
                ]])
            )
            return ConversationHandler.END
        
        # Валидация и преобразование значения
        try:
            if field_type == 'price':
                new_value = float(new_value)
                if new_value < 0:
                    raise ValueError("Стоимость должна быть положительным числом")
            elif field_type == 'duration':
                new_value = int(new_value)
                if new_value < 5:
                    raise ValueError("Длительность должна быть не менее 5 минут")
            elif field_type == 'name' and len(new_value) > 100:
                raise ValueError("Название должно быть короче 100 символов")
            elif field_type == 'description' and len(new_value) > 500:
                raise ValueError("Описание должно быть короче 500 символов")
        except ValueError as e:
            await update.message.reply_text(
                f"❌ Ошибка: {str(e)}. Попробуйте ещё раз:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Отмена", callback_data=f"edit_service_{service_id}")
                ]])
            )
            return EDIT_SERVICE_FIELD
        
        # Обновляем поле
        update_data = {field_type: new_value}
        service_update = ServiceUpdate(**update_data)
        updated_service = crud_service.update(db, db_obj=service, obj_in=service_update)
        
        # Очищаем данные редактирования
        del context.user_data['edit_service']
        
        await update.message.reply_text(
            f"✅ {field_type.capitalize()} успешно обновлено!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« К услуге", callback_data=f"edit_service_{service_id}")
            ]])
        )
        return ConversationHandler.END
    finally:
        db.close()

async def confirm_delete_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение удаления услуги"""
    query = update.callback_query
    service_id = int(query.data.split('_')[-1])
    db = SessionLocal()
    
    try:
        service = crud_service.remove(db, id=service_id)
        if service:
            await query.message.edit_text(
                f"✅ Услуга {service.name} успешно удалена",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« К списку услуг", callback_data="manage_services")
                ]])
            )
        else:
            await query.message.edit_text(
                "❌ Ошибка при удалении услуги",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« К списку услуг", callback_data="manage_services")
                ]])
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

async def start_add_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса добавления услуги"""
    user_id = update.effective_user.id
    service_data[user_id] = {}
    
    await update.callback_query.message.edit_text(
        "Введите название услуги:",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("« Отмена", callback_data="manage_services")
        ]])
    )
    return ENTER_SERVICE_NAME

async def enter_service_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода названия услуги"""
    user_id = update.effective_user.id
    name = update.message.text
    
    if len(name) > 100:
        await update.message.reply_text(
            "Название слишком длинное. Пожалуйста, введите название короче 100 символов:"
        )
        return ENTER_SERVICE_NAME
    
    service_data[user_id]['name'] = name
    await update.message.reply_text(
        "Введите описание услуги (или отправьте /skip чтобы пропустить):",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("« Отмена", callback_data="manage_services")
        ]])
    )
    return ENTER_SERVICE_DESCRIPTION

async def skip_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пропуск ввода описания"""
    user_id = update.effective_user.id
    service_data[user_id]['description'] = None
    await update.message.reply_text(
        "Введите стоимость услуги (только число):",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("« Отмена", callback_data="manage_services")
        ]])
    )
    return ENTER_SERVICE_PRICE

async def enter_service_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода описания услуги"""
    user_id = update.effective_user.id
    description = update.message.text
    
    if len(description) > 500:
        await update.message.reply_text(
            "Описание слишком длинное. Пожалуйста, введите описание короче 500 символов:"
        )
        return ENTER_SERVICE_DESCRIPTION
    
    service_data[user_id]['description'] = description
    await update.message.reply_text(
        "Введите стоимость услуги (только число):",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("« Отмена", callback_data="manage_services")
        ]])
    )
    return ENTER_SERVICE_PRICE

async def enter_service_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода стоимости услуги"""
    user_id = update.effective_user.id
    price_text = update.message.text
    
    try:
        price = float(price_text)
        if price < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "Пожалуйста, введите корректную стоимость (положительное число):"
        )
        return ENTER_SERVICE_PRICE
    
    service_data[user_id]['price'] = price
    await update.message.reply_text(
        "Введите длительность услуги в минутах (только число):",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("« Отмена", callback_data="manage_services")
        ]])
    )
    return ENTER_SERVICE_DURATION

async def enter_service_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода длительности услуги"""
    user_id = update.effective_user.id
    duration_text = update.message.text
    
    try:
        duration = int(duration_text)
        if duration < 5:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "Пожалуйста, введите корректную длительность (целое число не менее 5 минут):"
        )
        return ENTER_SERVICE_DURATION
    
    service_data[user_id]['duration'] = duration
    
    # Показываем сводку для подтверждения
    service = service_data[user_id]
    text = (
        f"Проверьте данные услуги:\n\n"
        f"Название: {service['name']}\n"
        f"Описание: {service['description'] or 'Нет'}\n"
        f"Стоимость: {service['price']}₽\n"
        f"Длительность: {service['duration']} минут\n\n"
        f"Всё верно?"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Да", callback_data="confirm_service"),
            InlineKeyboardButton("❌ Нет", callback_data="manage_services")
        ]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    return CONFIRM_SERVICE

async def confirm_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение и сохранение новой услуги"""
    user_id = update.effective_user.id
    db = SessionLocal()
    
    try:
        service_in = ServiceCreate(
            name=service_data[user_id]['name'],
            description=service_data[user_id]['description'],
            price=service_data[user_id]['price'],
            duration=service_data[user_id]['duration']
        )
        service = crud_service.create(db, obj_in=service_in)
        
        await update.callback_query.message.edit_text(
            f"✅ Услуга '{service.name}' успешно добавлена!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« К списку услуг", callback_data="manage_services")
            ]])
        )
    except Exception as e:
        await update.callback_query.message.edit_text(
            f"❌ Ошибка при сохранении услуги: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« К списку услуг", callback_data="manage_services")
            ]])
        )
    finally:
        db.close()
        if user_id in service_data:
            del service_data[user_id]
    
    return ConversationHandler.END

async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Админ панель"""
    keyboard = [
        [InlineKeyboardButton("📋 Управление услугами", callback_data="manage_services")],
        [InlineKeyboardButton("📅 Управление расписанием", callback_data="manage_schedule")],
        [InlineKeyboardButton("👥 Просмотр записей", callback_data="view_appointments")],
        [InlineKeyboardButton("« Назад", callback_data="start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.message.edit_text(
            "Панель администратора:",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "Панель администратора:",
            reply_markup=reply_markup
        )
