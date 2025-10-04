# 🔥 AiAlphaPulse

Система автоматического анализа финансовых новостей с использованием AI. Парсит новости из RSS и Telegram каналов, обрабатывает их, оценивает важность (hotness), кластеризует и отправляет уведомления через Telegram бот.

## 🎯 Основные возможности

- **Парсинг новостей**: RSS фиды + Telegram каналы
- **Автоматическая обработка**: нормализация, дедупликация, кластеризация
- **AI оценка важности**: каждая новость получает hotness (0-1) через Claude/GPT
- **Детальный анализ**: генерация аналитических отчётов для важных новостей
- **Telegram бот**: команды `/top`, `/latest`, подписки на горячие новости
- **Непрерывная работа**: Docker-контейнеры с автоматическим перезапуском

---

## 📦 Быстрый старт (локально)

### 1. Требования

- Python 3.11+
- PostgreSQL 12+ (с БД и данными от парсера)
- OpenRouter API ключ ([получить здесь](https://openrouter.ai))
- Telegram Bot токен (от [@BotFather](https://t.me/BotFather))
- Telegram API ID/Hash (для парсинга каналов, [получить здесь](https://my.telegram.org))

### 2. Установка

```bash
# Клонируйте репозиторий
git clone <your-repo-url>
cd AiAlphaPulse

# Установите зависимости
pip install -r requirements.txt

# Скачайте NLTK данные
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('wordnet')"
```

### 3. Настройка `.env`

Создайте файл `.env` в корне проекта:

```env
# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=alphapulse
POSTGRES_USER=admin
POSTGRES_PASSWORD=your-password

# OpenRouter API
OPENROUTER_API_KEY=sk-or-v1-your-key
LLM_MODEL=anthropic/claude-3.5-haiku
LLM_ANALYSIS_MODEL=anthropic/claude-3.5-sonnet
LLM_DELAY=1.0

# Pipeline
PIPELINE_CHECK_INTERVAL=300
PIPELINE_BATCH_SIZE=100
PIPELINE_LLM_LIMIT=50

# Telegram Bot
TELEGRAM_BOT_TOKEN=your-bot-token
HOT_NEWS_THRESHOLD=0.7
HOT_NEWS_INTERVAL=60

# Telegram API (для парсинга каналов)
TELEGRAM_API_ID=your-api-id
TELEGRAM_API_HASH=your-api-hash
TELEGRAM_PHONE=+1234567890

# Parser настройки
PARSER_CHECK_INTERVAL=300
PARSER_BATCH_SIZE=50
```

### 4. Запуск парсера (опционально)

Если у вас нет данных от парсера, запустите его:

```bash
# Парсинг RSS и Telegram каналов
python parser_worker.py
```

### 5. Обработка новостей

**Последовательно запустите 3 этапа:**

```bash
# Этап 1: Нормализация статей
python src/normalization/process_articles.py --batch-size 1000

# Этап 2: Дедупликация и кластеризация
python src/dedup/runner.py --max-docs 10000

# Этап 3: LLM анализ
python src/llm/runner.py --limit 500
```

### 6. Запуск Telegram бота

```bash
python run_telegram_bot.py
```

**Доступные команды в боте:**
- `/start` - приветствие и список команд
- `/top [N] [hours]` - топ новостей по hotness
- `/latest [N]` - последние добавленные новости
- `/subscribe` - подписаться на уведомления
- `/help` - справка

---

## 🐳 Развертывание в Docker

### Для production на сервере:

```bash
# 1. Убедитесь что .env файл заполнен
cat .env

# 2. Соберите образы
docker-compose build

# 3. Запустите все сервисы
docker-compose up -d

# 4. Проверьте логи
docker-compose logs -f
```

**Запущенные сервисы:**
- `parser` - парсинг RSS и Telegram каналов (каждые 5 минут)
- `pipeline` - обработка новостей (нормализация → дедупликация → LLM)
- `telegram_bot` - Telegram бот с автоуведомлениями

### Управление контейнерами:

```bash
# Остановить все
docker-compose down

# Перезапустить все
docker-compose restart

# Логи конкретного сервиса
docker-compose logs -f parser
docker-compose logs -f pipeline
docker-compose logs -f telegram_bot

# Запустить только парсер
docker-compose up parser -d

# Запустить только обработку
docker-compose up pipeline -d
```

---

## 📊 Архитектура

### Пайплайн обработки:

```
[0] Парсер → financial_news_view (RSS + Telegram)
    ↓
[1] Нормализация → normalized_articles
    ↓
[2] Векторизация + Кластеризация → story_clusters + vectors
    ↓
[3] LLM анализ (hotness) → llm_analyzed_news
    ↓
[4] Telegram бот → уведомления подписчикам
```

### Таблицы БД:

| Таблица | Описание |
|---------|----------|
| `financial_news_view` | Сырые новости от парсера |
| `normalized_articles` | Очищенные статьи с метаданными |
| `vectors` | Эмбеддинги для similarity search |
| `story_clusters` | Кластеры похожих новостей |
| `cluster_members` | Связь статей и кластеров |
| `llm_analyzed_news` | Результаты AI анализа |
| `telegram_subscribers` | Подписчики на уведомления |

### Компоненты:

```
src/
├── parser/            # Парсинг RSS и Telegram каналов
├── database/          # PostgreSQL подключение
├── normalization/     # Очистка и нормализация текста
├── dedup/             # FAISS векторизация + кластеризация
├── llm/               # OpenRouter AI анализ
└── telegram/          # Telegram бот
```

---

## 🔧 Основные скрипты

### Парсинг новостей:

```bash
# Парсинг RSS и Telegram каналов
python parser_worker.py
```

### Обработка новостей:

```bash
# Нормализация
python src/normalization/process_articles.py --batch-size 1000

# Дедупликация
python src/dedup/runner.py --max-docs 10000 --k-neighbors 30

# LLM анализ (оценка hotness)
python src/llm/runner.py --limit 500 --delay 1.0
```

### Telegram бот:

```bash
# Запуск бота с автоуведомлениями
python run_telegram_bot.py
```

### Pipeline воркер:

```bash
# Непрерывная обработка (запускается в Docker)
python pipeline_worker.py
```
---

## ⚙️ Настройка LLM моделей

Система использует **две модели** для разных задач:

### `LLM_MODEL` - для оценки hotness (дешёвая, быстрая)

Рекомендуемые варианты:
- `anthropic/claude-3.5-haiku` ⭐ (лучший выбор)
- `meta-llama/llama-3.3-70b-instruct` (бесплатная)

### `LLM_ANALYSIS_MODEL` - для детального анализа (мощная) 

Рекомендуемые варианты:
- `anthropic/claude-3.5-sonnet` ⭐ (лучший выбор)
- `mistralai/mistral-large`

**Проверка доступности модели:**

```bash
python -c "
import os, requests
from dotenv import load_dotenv
load_dotenv()

response = requests.post(
    'https://openrouter.ai/api/v1/chat/completions',
    headers={'Authorization': f'Bearer {os.getenv(\"OPENROUTER_API_KEY\")}'},
    json={'model': 'anthropic/claude-3.5-haiku', 'messages': [{'role': 'user', 'content': 'Hi'}], 'max_tokens': 5}
)
print('✅ Модель доступна' if response.status_code == 200 else f'❌ Ошибка: {response.status_code}')
"
```

---

## 📱 Telegram команды

| Команда | Описание | Пример |
|---------|----------|--------|
| `/start` | Приветствие | - |
| `/top [N] [hours]` | Топ по hotness | `/top 10 24` |
| `/latest [N]` | Последние новости | `/latest 5` |
| `/subscribe` | Подписка на алерты | - |
| `/unsubscribe` | Отписка | - |
| `/mystatus` | Статус подписки | - |
| `/help` | Справка | - |

---

## 📈 Мониторинг

```bash
# Статистика БД
python -c "
from src.database.postgres_connection import PostgreSQLConnection
db = PostgreSQLConnection()
db.connect()
cursor = db._connection.cursor()

cursor.execute('SELECT COUNT(*) FROM normalized_articles')
print(f'Нормализовано статей: {cursor.fetchone()[0]:,}')

cursor.execute('SELECT COUNT(*) FROM story_clusters')
print(f'Кластеров: {cursor.fetchone()[0]:,}')

cursor.execute('SELECT COUNT(*) FROM llm_analyzed_news')
print(f'Проанализировано LLM: {cursor.fetchone()[0]:,}')

db.close()
"
```

---

## 👥 Контакты

Вопросы и предложения: telegram: @smn_v
