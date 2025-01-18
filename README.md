# Telegram Booking Mini App

Приложение для записи клиентов через Telegram Mini App.

## Особенности

- Запись клиентов с выбором услуги и времени
- Управление расписанием и услугами для мастеров
- Уведомления для мастеров и клиентов
- Административная панель
- Интеграция с Telegram Mini App

## Технологии

- Backend:
  - FastAPI (Python)
  - SQLAlchemy
  - PostgreSQL
  - Alembic для миграций

- Frontend:
  - React
  - Telegram Web App SDK
  - React Router

## Требования

- Docker и Docker Compose
- Telegram Bot Token

## Установка и запуск

1. Клонируйте репозиторий:
   ```bash
   git clone <repository-url>
   cd telegram-booking-app
   ```

2. Создайте файл .env на основе .env.example:
   ```bash
   cp .env.example .env
   ```

3. Отредактируйте .env и добавьте ваш Telegram Bot Token:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   ```

4. Запустите приложение с помощью Docker Compose:
   ```bash
   docker-compose up -d
   ```

5. Примените миграции базы данных:
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

## Настройка Telegram Mini App

1. Создайте бота через @BotFather в Telegram

2. Получите токен бота и добавьте его в .env файл

3. Создайте Mini App через @BotFather:
   - Отправьте команду /newapp
   - Выберите бота, для которого создаете Mini App
   - Укажите название и описание
   - Укажите URL вашего веб-приложения

4. Настройте веб-приложение:
   - URL: http://your-domain/
   - Поддержка запуска через Telegram Web Apps: Включено

## Структура проекта

```
telegram-booking-app/
├── app/                    # Backend приложение
│   ├── api/               # API endpoints
│   ├── bot/               # Telegram bot handlers
│   ├── core/              # Основные настройки
│   ├── crud/              # CRUD операции
│   ├── db/                # Настройки базы данных
│   ├── models/            # Модели данных
│   └── schemas/           # Pydantic schemas
├── webapp/                # Frontend приложение
│   ├── src/              # Исходный код React
│   ├── public/           # Статические файлы
│   └── package.json      # Зависимости
├── alembic/              # Миграции базы данных
├── docker-compose.yml    # Docker Compose конфигурация
└── README.md            # Документация
```

## Разработка

### Backend

1. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

2. Запустите сервер разработки:
   ```bash
   uvicorn app.main:app --reload
   ```

### Frontend

1. Перейдите в директорию webapp:
   ```bash
   cd webapp
   ```

2. Установите зависимости:
   ```bash
   npm install
   ```

3. Запустите сервер разработки:
   ```bash
   npm start
   ```

## API Документация

После запуска приложения, документация API доступна по адресу:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Лицензия

MIT