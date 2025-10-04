# 🤖 Настройка LLM анализа новостей

## Шаг 1: Получите API ключ OpenRouter

1. Зайдите на https://openrouter.ai/
2. Зарегистрируйтесь или войдите
3. Перейдите на https://openrouter.ai/keys
4. Создайте новый API ключ
5. **Важно**: Пополните баланс на https://openrouter.ai/credits (минимум $1)

## Шаг 2: Установите API ключ

### Вариант 1: Автоматическая настройка (рекомендуется)

```bash
./setup_env.sh
```

Скрипт создаст `.env` файл и попросит ввести API ключ.

### Вариант 2: Ручная настройка

```bash
# Скопируйте пример
cp .env.example .env

# Отредактируйте файл
nano .env

# Вставьте ваш ключ:
OPENROUTER_API_KEY=sk-or-v1-ваш-ключ-здесь
```

### Вариант 3: Через переменные окружения (временно)

```bash
export OPENROUTER_API_KEY='sk-or-v1-ваш-ключ-здесь'
```

## Шаг 3: Проверьте подключение

```bash
cd /Users/semenisaev/AiAlphaPulse
python3 test_openrouter.py
```

Должно быть:
```
✅ API ключ найден: sk-or-v1-...
✅ API работает!
```

## Шаг 4: Запустите обработку

```bash
# Тест на 2 кластерах
python3 -m src.llm.runner --limit 2 --delay 2

# Обработать 10 кластеров
python3 -m src.llm.runner --limit 10

# Обработать все
python3 -m src.llm.runner --limit 115
```

## Шаг 5: Посмотрите результаты

```bash
# Топ-10 самых горячих новостей
python3 -m src.llm.runner --show-top 10

# Или через SQL
python3 << 'EOF'
from src.database import get_db_cursor

with get_db_cursor() as cursor:
    cursor.execute("""
        SELECT headline, ai_hotness, tickers_json 
        FROM llm_analyzed_news 
        ORDER BY ai_hotness DESC 
        LIMIT 10
    """)
    
    for i, row in enumerate(cursor.fetchall(), 1):
        print(f"{i}. {row['headline'][:70]}...")
        print(f"   🔥 {row['ai_hotness']:.3f} | 📊 {row['tickers_json']}\n")
EOF
```

## Стоимость

**GPT-3.5-turbo** (рекомендуется для теста):
- ~$0.0005 за новость
- 115 кластеров = ~$0.06

**GPT-4** (лучшее качество):
- ~$0.015 за новость  
- 115 кластеров = ~$1.70

## Решение проблем

### Ошибка 403 Forbidden
- Проверьте API ключ на https://openrouter.ai/keys
- Проверьте баланс на https://openrouter.ai/credits
- Убедитесь, что ключ активен

### Ошибка 429 Rate Limit
- Увеличьте `--delay` (например `--delay 5`)
- Подождите несколько минут

### Ошибка подключения
- Проверьте интернет соединение
- Проверьте статус OpenRouter: https://openrouter.ai/

