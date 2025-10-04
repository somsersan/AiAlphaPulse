#!/bin/bash

echo "🚀 Запуск AiAlphaPulse - Полный пайплайн"
echo "========================================"

# Проверяем наличие Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не установлен. Пожалуйста, установите Python 3."
    exit 1
fi

# Проверяем наличие зависимостей
if [ ! -d "venv" ]; then
    echo "📦 Создаем виртуальное окружение..."
    python3 -m venv venv
    source venv/bin/activate
    echo "📥 Устанавливаем зависимости..."
    pip install -r requirements.txt
else
    echo "✅ Виртуальное окружение найдено"
    source venv/bin/activate
fi

# Проверяем параметры
INTERVAL=${1:-300}  # По умолчанию 5 минут
K_NEIGHBORS=${2:-30}
TOP_K=${3:-10}
WINDOW_HOURS=${4:-48}

echo ""
echo "⚙️  Параметры запуска:"
echo "   - Интервал: $INTERVAL секунд"
echo "   - K-neighbors: $K_NEIGHBORS"
echo "   - Top-K кластеров: $TOP_K"
echo "   - Временное окно: $WINDOW_HOURS часов"
echo ""

# Проверяем доступность базы данных
echo "🔍 Проверяем подключение к базе данных..."
python3 << EOF
import sys
try:
    from src.database import get_db_connection
    conn = get_db_connection()
    conn.connect()
    print("✅ База данных доступна")
    conn.close()
except Exception as e:
    print(f"❌ Ошибка подключения к БД: {e}")
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    echo "❌ Не удалось подключиться к базе данных"
    exit 1
fi

# Инициализируем базу данных
echo ""
echo "🔄 Инициализация базы данных..."
python3 init_db.py

if [ $? -ne 0 ]; then
    echo "⚠️  Ошибка инициализации БД, но продолжаем..."
fi

# Запускаем пайплайн
echo ""
echo "🎯 Запускаем автоматический пайплайн..."
echo "   (Для остановки нажмите Ctrl+C)"
echo ""

python3 run_pipeline.py \
    --interval $INTERVAL \
    --k-neighbors $K_NEIGHBORS \
    --top-k $TOP_K \
    --window-hours $WINDOW_HOURS

echo ""
echo "✅ Пайплайн остановлен"

