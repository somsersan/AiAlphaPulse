"""
Доменные сущности для системы парсинга новостей.
Содержит основные бизнес-объекты без привязки к конкретной реализации.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from enum import Enum


class SourceType(Enum):
    """Типы источников новостей."""
    RSS = "rss"
    TELEGRAM = "telegram"
    API = "api"


@dataclass
class Article:
    """Доменная сущность статьи."""
    id: Optional[int]
    title: str
    link: str
    published: Optional[datetime]
    summary: Optional[str]
    source: str
    feed_url: str
    content: Optional[str]
    author: Optional[str]
    category: Optional[str]
    image_url: Optional[str]
    word_count: int
    reading_time: int
    is_processed: bool
    created_at: datetime

    def __post_init__(self):
        """Валидация данных после инициализации."""
        if not self.title:
            raise ValueError("Title cannot be empty")
        if not self.link:
            raise ValueError("Link cannot be empty")
        if self.word_count < 0:
            raise ValueError("Word count cannot be negative")
        if self.reading_time < 0:
            raise ValueError("Reading time cannot be negative")

    @property
    def is_financial_news(self) -> bool:
        """Проверяет, является ли статья финансовой новостью."""
        financial_keywords = [
            'акции', 'облигации', 'рубль', 'доллар', 'евро', 'нефть', 'золото',
            'инфляция', 'процент', 'кредит', 'банк', 'инвестиции', 'рынок',
            'бирж', 'торг', 'котировк', 'индекс', 'дивиденд', 'ipo'
        ]
        text = (self.title + " " + (self.summary or "") + " " + (self.content or "")).lower()
        return any(keyword in text for keyword in financial_keywords)

    def calculate_reading_stats(self) -> None:
        """Пересчитывает статистику чтения."""
        if not self.content:
            self.word_count = 0
            self.reading_time = 0
            return

        # Подсчет слов (простая логика)
        import re
        words = re.findall(r'\b\w+\b', self.content.lower())
        self.word_count = len(words)
        
        # Время чтения (примерно 200 слов в минуту)
        self.reading_time = max(1, self.word_count // 200)


@dataclass
class ParsingStats:
    """Статистика парсинга."""
    total_articles: int
    processed_articles: int
    avg_words: float
    sources: List[dict]
    last_run: Optional[datetime] = None
    is_running: bool = False

    @property
    def processing_rate(self) -> float:
        """Процент обработанных статей."""
        if self.total_articles == 0:
            return 0.0
        return (self.processed_articles / self.total_articles) * 100


@dataclass
class RSSFeed:
    """RSS лента."""
    url: str
    title: str
    is_active: bool = True
    last_parsed: Optional[datetime] = None
    error_count: int = 0

    def __post_init__(self):
        if not self.url:
            raise ValueError("URL cannot be empty")


@dataclass
class TelegramChannel:
    """Telegram канал."""
    username: str
    display_name: str
    is_active: bool = True
    last_parsed: Optional[datetime] = None
    error_count: int = 0

    def __post_init__(self):
        if not self.username:
            raise ValueError("Username cannot be empty")
        if not self.username.startswith('@'):
            self.username = f"@{self.username}"
