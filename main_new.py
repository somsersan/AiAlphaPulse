"""
Главный файл приложения с чистой архитектурой.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import threading
import time
from datetime import datetime

# Импорты из конфигурации
from config.settings import settings

# Импорты из инфраструктуры
from infrastructure.database.connection import db_connection, DatabaseConnection
from infrastructure.database.repositories import SQLArticleRepository, SQLFeedRepository
from infrastructure.parsers.rss_parser import RSSParser
from infrastructure.parsers.telegram_parser import TelegramParser
from infrastructure.parsers.api_parser import APIParser
from infrastructure.external.feed_initializer import FeedInitializer

# Импорты из сервисов
from core.services.article_service import ArticleService
from core.services.parsing_service import ParsingService

# Импорты из use cases
from core.use_cases.get_articles_use_case import GetArticlesUseCase
from core.use_cases.parse_news_use_case import ParseNewsUseCase
from core.use_cases.get_stats_use_case import GetStatsUseCase

# Импорты из API
from infrastructure.api.controllers import ArticleController, ParsingController, StatsController
from infrastructure.api.schemas import ArticleResponse, StatsResponse, ParseResponse, HealthResponse

# Глобальные переменные для DI контейнера
article_repository = None
feed_repository = None
article_service = None
parsing_service = None
article_controller = None
parsing_controller = None
stats_controller = None


def setup_dependency_injection():
    """Настраивает внедрение зависимостей."""
    global article_repository, feed_repository, article_service, parsing_service
    global article_controller, parsing_controller, stats_controller
    
    # Создаем репозитории
    article_repository = SQLArticleRepository()
    feed_repository = SQLFeedRepository()
    
    # Создаем парсеры
    rss_parser = RSSParser()
    telegram_parser = TelegramParser()
    API_parser = APIParser(settings.crypto)
    
    # Создаем сервисы
    article_service = ArticleService(article_repository)
    parsing_service = ParsingService(article_repository, feed_repository, rss_parser, telegram_parser, API_parser)
    
    # Создаем use cases
    get_articles_use_case = GetArticlesUseCase(article_service)
    parse_news_use_case = ParseNewsUseCase(parsing_service)
    get_stats_use_case = GetStatsUseCase(article_service)
    
    # Создаем контроллеры
    article_controller = ArticleController(get_articles_use_case)
    parsing_controller = ParsingController(parse_news_use_case)
    stats_controller = StatsController(get_stats_use_case)


# Lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Запуск RSS Parser API с чистой архитектурой...")
    
    # Инициализация базы данных
    try:
        if not DatabaseConnection.wait_for_database():
            raise Exception("Database connection failed")
        
        db_connection.create_tables()
        print("✅ База данных инициализирована")
    except Exception as e:
        print(f"❌ Ошибка инициализации базы данных: {e}")
        raise
    
    # Настройка DI
    setup_dependency_injection()
    print("✅ Внедрение зависимостей настроено")
    
    # Инициализация лент и каналов
    try:
        feed_initializer = FeedInitializer()
        await feed_initializer.initialize_feeds()
        print("✅ Ленты и каналы инициализированы")
    except Exception as e:
        print(f"❌ Ошибка инициализации лент: {e}")
    
    # Запуск фоновой задачи
    thread = threading.Thread(target=auto_parse_worker, daemon=True)
    thread.start()
    print("🔄 Автоматический парсинг запущен")
    
    yield
    
    # Shutdown
    print("🛑 Остановка RSS Parser API...")


# Создаем FastAPI приложение
app = FastAPI(
    title=settings.api.title,
    description=settings.api.description,
    version=settings.api.version,
    lifespan=lifespan
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def auto_parse_worker():
    """Фоновая задача для автоматического парсинга."""
    while True:
        try:
            print(f"🔄 Автоматический парсинг запущен в {datetime.now()}")
            
            # Запускаем парсинг в новом event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(parsing_service.parse_all_sources())
                print(f"✅ Парсинг завершен. Добавлено статей: {result.get('total', 0)}")
                print(f"📊 Детализация:")
                print(f"   - RSS: {result.get('rss', 0)} статей")
                print(f"   - Telegram: {result.get('telegram', 0)} статей")
                print(f"   - API (криптовалюты): {result.get('api', 0)} статей")
            finally:
                loop.close()
            
        except Exception as e:
            print(f"❌ Ошибка в автоматическом парсинге: {e}")
        
        # Ждем указанное время
        time.sleep(settings.parsing.auto_parse_interval)


# API эндпоинты
@app.get("/", response_model=dict)
async def root():
    """Главная страница API."""
    return {
        "message": settings.api.title,
        "version": settings.api.version,
        "status": "running",
        "architecture": "clean_architecture",
        "auto_parsing": f"enabled (every {settings.parsing.auto_parse_interval} seconds)"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Проверка здоровья приложения."""
    return await stats_controller.get_health()


@app.post("/parse", response_model=ParseResponse)
async def manual_parse():
    """Ручной запуск парсинга всех источников."""
    return await parsing_controller.parse_all()


@app.post("/parse/rss", response_model=ParseResponse)
async def manual_parse_rss():
    """Ручной запуск парсинга только RSS-лент."""
    return await parsing_controller.parse_rss()


@app.post("/parse/telegram", response_model=ParseResponse)
async def manual_parse_telegram():
    """Ручной запуск парсинга только Telegram каналов."""
    return await parsing_controller.parse_telegram()


@app.get("/articles", response_model=list[ArticleResponse])
async def get_articles(limit: int = 10, source: str = None):
    """Получить последние статьи."""
    return await article_controller.get_articles(limit, source)


@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Получить статистику по статьям."""
    return await stats_controller.get_stats()


@app.get("/status")
async def get_parsing_status():
    """Получить статус автоматического парсинга."""
    return await parsing_service.get_parsing_status()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main_new:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.debug
    )
