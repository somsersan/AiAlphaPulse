#!/bin/bash

echo "🚀 Запуск RSS Parser API с Docker Compose..."

# Проверяем наличие Docker и Docker Compose
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Пожалуйста, установите Docker."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не установлен. Пожалуйста, установите Docker Compose."
    exit 1
fi

# Создаем директорию для логов
mkdir -p logs

# Останавливаем существующие контейнеры
echo "🛑 Остановка существующих контейнеров..."
docker-compose down

# Собираем и запускаем сервисы
echo "🔨 Сборка и запуск сервисов..."
docker-compose up --build -d

# Ждем запуска сервисов
echo "⏳ Ожидание запуска сервисов..."
sleep 10

# Проверяем статус
echo "📊 Статус сервисов:"
docker-compose ps

echo ""
echo "✅ RSS Parser API запущен!"
echo ""
echo "🌐 Доступные сервисы:"
echo "   - FastAPI приложение: http://localhost:8000"
echo "   - API документация: http://localhost:8000/docs"
echo "   - pgAdmin: http://localhost:8080 (admin@rss.com / admin123)"
echo ""
echo "📋 Полезные команды:"
echo "   - Просмотр логов: docker-compose logs -f"
echo "   - Остановка: docker-compose down"
echo "   - Перезапуск: docker-compose restart"
echo ""
echo "🔍 Для проверки работы API:"
echo "   curl http://localhost:8000/health"
