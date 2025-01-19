#!/bin/bash

# Проверяем наличие ngrok
if ! command -v ngrok &> /dev/null; then
    echo "ngrok не установлен. Устанавливаем..."
    curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null && echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list && sudo apt update && sudo apt install ngrok
fi

# Проверяем наличие .env файла
if [ ! -f .env ]; then
    echo "Создаем .env файл..."
    cp .env.example .env
    echo "Пожалуйста, добавьте TELEGRAM_BOT_TOKEN в .env файл"
    exit 1
fi

# Запускаем Docker Compose
echo "Запускаем приложение..."
docker-compose up -d

# Ждем, пока сервисы запустятся
echo "Ждем запуска сервисов..."
sleep 10

# Применяем миграции
echo "Применяем миграции базы данных..."
docker-compose exec backend alembic upgrade head

# Запускаем ngrok для фронтенда
echo "Запускаем ngrok для фронтенда..."
ngrok http 80 > ngrok.log 2>&1 &
NGROK_PID=$!

# Ждем, пока ngrok запустится
sleep 5

# Получаем URL от ngrok
NGROK_URL=$(curl -s localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url')

echo "============================================"
echo "Приложение запущено!"
echo "Фронтенд доступен по адресу: $NGROK_URL"
echo "API доступен по адресу: $NGROK_URL/api/v1"
echo "Swagger UI: $NGROK_URL/docs"
echo "============================================"
echo "Теперь необходимо:"
echo "1. Создать Mini App через @BotFather"
echo "2. Указать URL: $NGROK_URL"
echo "============================================"
echo "Для остановки нажмите Ctrl+C"

# Ожидаем сигнал завершения
trap "docker-compose down && kill $NGROK_PID" EXIT
wait