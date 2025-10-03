from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from contextlib import asynccontextmanager
import asyncio
import threading
import time
from datetime import datetime
import uvicorn
from rss_parser import parse_and_save_rss, check_articles, get_articles_stats, setup_database

# Lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Запуск RSS Parser API...")
    
    # Инициализация базы данных
    try:
        setup_database()
        print("✅ База данных инициализирована")
    except Exception as e:
        print(f"❌ Ошибка инициализации базы данных: {e}")
    
    # Запуск фоновой задачи в отдельном потоке
    thread = threading.Thread(target=auto_parse_worker, daemon=True)
    thread.start()
    print("🔄 Автоматический парсинг запущен (каждую минуту)")
    
    yield
    
    # Shutdown (if needed)
    print("🛑 Остановка RSS Parser API...")

# Создаем FastAPI приложение
app = FastAPI(
    title="RSS Parser API",
    description="API для парсинга RSS-лент с автоматическим обновлением каждую минуту",
    version="1.0.0",
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

# Pydantic модели для API
class ArticleResponse(BaseModel):
    id: int
    source: str
    title: str
    author: Optional[str]
    category: Optional[str]
    published: Optional[str]
    created_at: str
    word_count: int
    reading_time: int
    is_processed: bool
    link: str
    image_url: Optional[str]
    summary: Optional[str]
    content: Optional[str]

class StatsResponse(BaseModel):
    total_articles: int
    processed_articles: int
    avg_words: float
    sources: List[dict]

class ParseResponse(BaseModel):
    message: str
    new_articles_count: int
    timestamp: str

# Глобальная переменная для отслеживания статуса парсинга
parsing_status = {
    "is_running": False,
    "last_run": None,
    "last_articles_count": 0
}

# Функция для автоматического парсинга
def auto_parse_worker():
    """Фоновая задача для автоматического парсинга каждую минуту."""
    global parsing_status
    
    while True:
        try:
            print(f"🔄 Автоматический парсинг запущен в {datetime.now()}")
            parsing_status["is_running"] = True
            
            new_count = parse_and_save_rss()
            parsing_status["last_run"] = datetime.now()
            parsing_status["last_articles_count"] = new_count
            parsing_status["is_running"] = False
            
            print(f"✅ Автоматический парсинг завершен. Добавлено статей: {new_count}")
            
        except Exception as e:
            print(f"❌ Ошибка в автоматическом парсинге: {e}")
            parsing_status["is_running"] = False
        
        # Ждем 60 секунд перед следующим парсингом
        time.sleep(60)


# API эндпоинты
@app.get("/", response_model=dict)
async def root():
    """Главная страница API."""
    return {
        "message": "RSS Parser API",
        "version": "1.0.0",
        "status": "running",
        "auto_parsing": "enabled (every minute)"
    }

@app.get("/health")
async def health_check():
    """Проверка здоровья приложения."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "parsing_status": parsing_status
    }

@app.post("/parse", response_model=ParseResponse)
async def manual_parse():
    """Ручной запуск парсинга RSS-лент."""
    try:
        print("🔄 Ручной парсинг запущен")
        new_count = parse_and_save_rss()
        
        return ParseResponse(
            message="Парсинг завершен успешно",
            new_articles_count=new_count,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка парсинга: {str(e)}")

@app.get("/articles", response_model=List[ArticleResponse])
async def get_articles(limit: int = 10):
    """Получить последние статьи."""
    try:
        articles = check_articles(limit)
        return [ArticleResponse(**article) for article in articles]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения статей: {str(e)}")

@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Получить статистику по статьям."""
    try:
        stats = get_articles_stats()
        return StatsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения статистики: {str(e)}")

@app.get("/status")
async def get_parsing_status():
    """Получить статус автоматического парсинга."""
    return {
        "is_running": parsing_status["is_running"],
        "last_run": parsing_status["last_run"].isoformat() if parsing_status["last_run"] else None,
        "last_articles_count": parsing_status["last_articles_count"]
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
