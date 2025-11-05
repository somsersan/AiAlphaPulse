# 🚀 Быстрая шпаргалка по развертыванию AiAlphaPulse

## ⚡ Быстрый старт

```bash
# 1. Клонируем репозиторий
git clone <your-repo-url> AiAlphaPulse
cd AiAlphaPulse

# 2. Создаем .env файл
nano .env  # Заполняем все необходимые переменные

# 3. Собираем образы
docker compose build

# 4. Запускаем сервисы
docker compose up -d

# 5. Проверяем логи
docker compose logs -f
```

## 📝 Основные команды

### Управление контейнерами

```bash
# Запуск
docker compose up -d

# Остановка
docker compose stop

# Перезапуск
docker compose restart

# Остановка и удаление
docker compose down

# Статус
docker compose ps
```

### Логи

```bash
# Все логи
docker compose logs

# Логи pipeline
docker compose logs pipeline

# Логи telegram бота
docker compose logs telegram_bot

# Следить в реальном времени
docker compose logs -f pipeline

# Последние 100 строк
docker compose logs --tail=100 pipeline
```

### Пересборка

```bash
# Пересборка без кэша
docker compose build --no-cache

# Пересборка и перезапуск
docker compose up -d --build
```

### Обновление

```bash
# Остановка
docker compose down

# Обновление кода
git pull

# Пересборка
docker compose build

# Запуск
docker compose up -d
```

## 🔍 Проверка работы

```bash
# Статус контейнеров
docker compose ps

# Healthcheck
docker inspect alphapulse_pipeline | grep -A 10 Health

# Использование ресурсов
docker stats

# Проверка БД из контейнера
docker exec -it alphapulse_pipeline bash
python3 -c "from src.database import get_db_connection; conn = get_db_connection(); conn.connect(); print('OK'); conn.close()"
```

## 🐛 Устранение проблем

```bash
# Контейнер не запускается
docker compose logs pipeline | tail -50

# Перезапуск
docker compose restart pipeline

# Пересборка с нуля
docker compose down
docker compose build --no-cache
docker compose up -d

# Очистка всего
docker compose down -v
docker system prune -a
```

## 📋 Чеклист .env

Убедитесь что в `.env` установлены:

- [ ] `POSTGRES_HOST`
- [ ] `POSTGRES_PORT`
- [ ] `POSTGRES_DB`
- [ ] `POSTGRES_USER`
- [ ] `POSTGRES_PASSWORD`
- [ ] `PROXYAPI_KEY` ⚠️ ОБЯЗАТЕЛЬНО
- [ ] `TELEGRAM_BOT_TOKEN` ⚠️ ОБЯЗАТЕЛЬНО для бота
- [ ] `LLM_MODEL`
- [ ] `PIPELINE_CHECK_INTERVAL`
- [ ] `PIPELINE_BATCH_SIZE`
- [ ] `PIPELINE_LLM_LIMIT`

## 🔐 Безопасность

```bash
# Правильные права на .env
chmod 600 .env

# Проверка что .env не в git
grep .env .gitignore
```

## 📞 Полная документация

См. [DEPLOYMENT.md](./DEPLOYMENT.md) для подробной инструкции.

