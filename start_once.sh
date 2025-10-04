#!/bin/bash

echo "🎯 Запуск AiAlphaPulse - Однократный запуск"
echo "==========================================="

# Активируем виртуальное окружение
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ Виртуальное окружение не найдено. Запустите start_all.sh сначала."
    exit 1
fi

# Проверяем параметры
K_NEIGHBORS=${1:-30}
TOP_K=${2:-10}
WINDOW_HOURS=${3:-48}

echo ""
echo "⚙️  Параметры:"
echo "   - K-neighbors: $K_NEIGHBORS"
echo "   - Top-K кластеров: $TOP_K"
echo "   - Временное окно: $WINDOW_HOURS часов"
echo ""

# Запускаем один цикл
python3 run_pipeline.py \
    --once \
    --k-neighbors $K_NEIGHBORS \
    --top-k $TOP_K \
    --window-hours $WINDOW_HOURS

echo ""
echo "✅ Цикл завершен"

