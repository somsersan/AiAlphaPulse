# AiAlphaPulse - RSS & Telegram Parser API

Система для парсинга финансовых новостей из RSS-лент и Telegram каналов с чистой архитектурой.

## 🏗️ Архитектура

Проект построен на принципах **Clean Architecture**, что обеспечивает:

- ✅ **Разделение ответственности** - каждый слой имеет четко определенную роль
- ✅ **Тестируемость** - легко создавать unit-тесты для каждого компонента
- ✅ **Гибкость** - легко заменять реализации без изменения бизнес-логики
- ✅ **Масштабируемость** - простое добавление новых функций
- ✅ **Поддерживаемость** - изменения в одном слое не влияют на другие

### Структура проекта

```
AiAlphaPulse/
├── core/                    # 🧠 Ядро приложения (бизнес-логика)
│   ├── domain/             # Доменные сущности и правила
│   ├── repositories/       # Интерфейсы для работы с данными
│   ├── services/          # Бизнес-сервисы
│   └── use_cases/         # Сценарии использования
├── infrastructure/         # 🔧 Инфраструктурный слой
│   ├── database/          # Работа с базой данных
│   ├── parsers/           # Парсеры внешних источников
│   ├── api/               # API контроллеры
│   └── external/          # Внешние адаптеры
├── config/                # ⚙️ Конфигурация приложения
├── main_new.py           # 🚀 Главный файл приложения
└── Dockerfile            # 🐳 Контейнеризация
```

## 🚀 Быстрый старт

### Через Docker Compose (рекомендуется)

```bash
# Клонируйте репозиторий
git clone <repository-url>
cd AiAlphaPulse

# Запустите через Docker Compose
docker-compose up --build

# Приложение будет доступно по адресу: http://localhost:8000
```

### Локальный запуск

```bash
# Установите зависимости
pip install -r requirements.txt

# Настройте переменные окружения
cp .env.example .env
# Отредактируйте .env файл

# Запустите приложение
python main_new.py
```

## 📊 API Endpoints

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/` | Главная страница API |
| `GET` | `/health` | Проверка здоровья приложения |
| `GET` | `/articles` | Получение статей |
| `GET` | `/stats` | Статистика по статьям |
| `POST` | `/parse` | Ручной парсинг всех источников |
| `POST` | `/parse/rss` | Парсинг только RSS лент |
| `POST` | `/parse/telegram` | Парсинг только Telegram каналов |

### Примеры запросов

```bash
# Получить последние 10 статей
curl "http://localhost:8000/articles?limit=10"

# Получить статьи из конкретного источника
curl "http://localhost:8000/articles?source=RBCNews&limit=5"

# Запустить парсинг всех источников
curl -X POST "http://localhost:8000/parse"

# Получить статистику
curl "http://localhost:8000/stats"
```

## ⚙️ Конфигурация

Настройки приложения находятся в `config/settings.py` и могут быть переопределены через переменные окружения:

```bash
# База данных
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# API настройки
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=false

# Парсинг
PARSING_INTERVAL=60  # секунды
PARSING_MAX_RETRIES=3
PARSING_TIMEOUT=30

# RSS ленты (через запятую)
RSS_URLS=https://example1.com/rss,https://example2.com/rss

# Telegram каналы (через запятую)
TELEGRAM_CHANNELS=channel1,channel2,channel3
```

## 🏛️ Архитектурные принципы

### 1. Dependency Inversion
- Высокоуровневые модули не зависят от низкоуровневых
- Абстракции не зависят от деталей
- Детали зависят от абстракций

### 2. Single Responsibility
- Каждый класс имеет одну причину для изменения
- Четкое разделение ответственности между слоями

### 3. Open/Closed Principle
- Код открыт для расширения, закрыт для модификации
- Легко добавлять новые парсеры и источники данных

## 🧪 Тестирование

```bash
# Запуск тестов (когда будут добавлены)
pytest tests/

# Запуск с покрытием
pytest --cov=core tests/
```

## 📈 Мониторинг

- **Health Check**: `GET /health` - проверка состояния приложения
- **Статистика**: `GET /stats` - детальная статистика парсинга
- **Логи**: автоматическое логирование в папку `logs/`

## 🔧 Разработка

### Добавление нового парсера

1. Создайте класс парсера в `infrastructure/parsers/`
2. Реализуйте интерфейс парсера
3. Добавьте парсер в `ParsingService`
4. Обновите конфигурацию

### Добавление нового источника данных

1. Создайте модель в `infrastructure/database/models.py`
2. Добавьте репозиторий в `core/repositories/`
3. Реализуйте репозиторий в `infrastructure/database/repositories.py`
4. Обновите сервисы и use cases

## 🐳 Docker

```bash
# Сборка образа
docker build -t ai-alpha-pulse .

# Запуск контейнера
docker run -p 8000:8000 ai-alpha-pulse

# Запуск с переменными окружения
docker run -p 8000:8000 -e DATABASE_URL=postgresql://... ai-alpha-pulse
```

## 📝 Логирование

Приложение автоматически логирует:
- Запуск и остановку парсинга
- Ошибки при обработке источников
- Статистику добавленных статей
- Ошибки базы данных

## 🤝 Вклад в проект

1. Fork репозитория
2. Создайте feature branch (`git checkout -b feature/amazing-feature`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в branch (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## 📄 Лицензия

Этот проект распространяется под лицензией MIT. См. файл `LICENSE` для подробностей.

## 🆘 Поддержка

Если у вас есть вопросы или проблемы:

1. Проверьте [Issues](https://github.com/your-repo/issues)
2. Создайте новый Issue с подробным описанием
3. Обратитесь к [документации архитектуры](ARCHITECTURE.md)

---

**Сделано с ❤️ и принципами чистой архитектуры**
