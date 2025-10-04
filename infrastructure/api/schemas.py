"""
Pydantic схемы для API.
"""

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class ArticleResponse(BaseModel):
    """Схема ответа для статьи."""
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

    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    """Схема ответа для статистики."""
    total_articles: int
    processed_articles: int
    processing_rate: float
    avg_words: float
    sources: List[dict]
    last_run: Optional[str] = None
    is_running: bool = False


class ParseResponse(BaseModel):
    """Схема ответа для парсинга."""
    message: str
    new_articles_count: int
    timestamp: str
    details: Optional[dict] = None


class HealthResponse(BaseModel):
    """Схема ответа для проверки здоровья."""
    status: str
    timestamp: str
    parsing_status: dict


class ErrorResponse(BaseModel):
    """Схема ответа для ошибок."""
    error: str
    detail: str
    timestamp: str
