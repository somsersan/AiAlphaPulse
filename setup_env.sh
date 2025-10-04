#!/bin/bash

echo "🔧 Настройка .env файла для AiAlphaPulse"
echo "=========================================="
echo ""

# Проверяем наличие .env
if [ -f ".env" ]; then
    echo "⚠️  Файл .env уже существует"
    read -p "Перезаписать? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Отменено"
        exit 0
    fi
fi

# Копируем пример
cp .env.example .env

echo "✅ Создан файл .env"
echo ""

# Запрашиваем API ключ
echo "📝 Введите ваш OPENROUTER_API_KEY:"
echo "   (Получить можно на https://openrouter.ai/keys)"
read -p "API ключ: " api_key

if [ -z "$api_key" ]; then
    echo "⚠️  Ключ не введен, оставлен пример"
    echo ""
    echo "Отредактируйте .env файл вручную:"
    echo "  nano .env"
else
    # Заменяем ключ в файле
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s|OPENROUTER_API_KEY=.*|OPENROUTER_API_KEY=$api_key|" .env
    else
        # Linux
        sed -i "s|OPENROUTER_API_KEY=.*|OPENROUTER_API_KEY=$api_key|" .env
    fi
    echo "✅ API ключ сохранен в .env"
fi

echo ""
echo "=========================================="
echo "✅ Настройка завершена!"
echo ""
echo "Проверьте подключение:"
echo "  python3 test_openrouter.py"
echo ""
echo "Запустите обработку:"
echo "  python3 -m src.llm.runner --limit 2"
echo ""

