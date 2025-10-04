# RSS Parser API

FastAPI приложение для автоматического парсинга RSS-лент с PostgreSQL базой данных.

## Возможности

- 🔄 Автоматический парсинг RSS-лент каждую минуту
- 🗄️ PostgreSQL база данных для хранения статей
- 🚀 FastAPI REST API
- 🐳 Docker контейнеризация
- 📊 Статистика и мониторинг
- 🔍 Извлечение полного контента статей

## Структура проекта

```
simple-rss-parser/
├── main.py                    # FastAPI приложение
├── rss_parser_postgres.py     # RSS парсер с PostgreSQL
├── rss_parser.py             # Оригинальный парсер (SQLite)
├── requirements.txt          # Python зависимости
├── Dockerfile               # Docker образ
├── docker-compose.yml       # Docker Compose конфигурация
└── README.md               # Документация
```

## Быстрый запуск

### 1. Запуск с Docker Compose

```bash
# Клонируйте репозиторий
git clone <repository-url>
cd simple-rss-parser

# Запустите все сервисы
docker-compose up -d

# Проверьте статус
docker-compose ps
```

### 2. Доступ к сервисам

- **FastAPI приложение**: http://localhost:8000
- **API документация**: http://localhost:8000/docs
- **pgAdmin**: http://localhost:8080 (admin@rss.com / admin123)
- **PostgreSQL**: localhost:5432

## API Эндпоинты

### Основные эндпоинты

- `GET /` - Главная страница
- `GET /health` - Проверка здоровья
- `GET /status` - Статус парсинга
- `POST /parse` - Ручной запуск парсинга
- `GET /articles?limit=10` - Получить статьи
- `GET /stats` - Статистика

### Примеры запросов

```bash
# Получить последние 5 статей
curl http://localhost:8000/articles?limit=5

# Запустить ручной парсинг
curl -X POST http://localhost:8000/parse

# Получить статистику
curl http://localhost:8000/stats

# Проверить статус
curl http://localhost:8000/status
```

## Конфигурация

### Переменные окружения

- `DATABASE_URL` - URL подключения к PostgreSQL
- По умолчанию: `postgresql://rss_user:rss_password@localhost:5432/rss_db`

### RSS ленты

Настройте RSS ленты в файле `rss_parser_postgres.py` в переменной `RSS_URLS`:

```python
RSS_URLS = [
    'https://example.com/rss',
    'https://another-site.com/feed.xml',
    # добавьте свои RSS ленты
]
```

## Разработка

### Локальная разработка

```bash
# Установите зависимости
pip install -r requirements.txt

# Запустите PostgreSQL локально или через Docker
docker run -d --name postgres \
  -e POSTGRES_DB=rss_db \
  -e POSTGRES_USER=rss_user \
  -e POSTGRES_PASSWORD=rss_password \
  -p 5432:5432 \
  postgres:15-alpine

# Установите переменную окружения
export DATABASE_URL="postgresql://rss_user:rss_password@localhost:5432/rss_db"

# Запустите приложение
python main.py
```

### Структура базы данных

Таблица `articles`:
- `id` - Уникальный идентификатор
- `title` - Заголовок статьи
- `link` - Ссылка на статью
- `published` - Дата публикации
- `summary` - Краткое описание
- `source` - Источник (название RSS ленты)
- `feed_url` - URL RSS ленты
- `content` - Полный текст статьи
- `author` - Автор
- `category` - Категория/теги
- `image_url` - URL изображения
- `word_count` - Количество слов
- `reading_time` - Время чтения в минутах
- `is_processed` - Статус обработки
- `created_at` - Дата добавления в БД

## Мониторинг

### Логи

```bash
# Просмотр логов приложения
docker-compose logs -f rss_parser

# Просмотр логов PostgreSQL
docker-compose logs -f postgres
```

### Статистика

Используйте эндпоинт `/stats` для получения статистики:
- Общее количество статей
- Количество обработанных статей
- Среднее количество слов
- Статистика по источникам

## Остановка и очистка

```bash
# Остановить сервисы
docker-compose down

# Остановить и удалить данные
docker-compose down -v

# Удалить образы
docker-compose down --rmi all
```

## Troubleshooting

### Проблемы с подключением к БД

1. Убедитесь, что PostgreSQL запущен
2. Проверьте переменную `DATABASE_URL`
3. Проверьте логи: `docker-compose logs postgres`

### Проблемы с парсингом

1. Проверьте доступность RSS лент
2. Проверьте логи приложения: `docker-compose logs rss_parser`
3. Используйте эндпоинт `/status` для проверки статуса

### Проблемы с Docker

1. Убедитесь, что Docker и Docker Compose установлены
2. Проверьте доступность портов 8000, 5432, 8080
3. Пересоберите образы: `docker-compose build --no-cache`
