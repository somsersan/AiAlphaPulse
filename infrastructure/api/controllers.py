"""
API контроллеры.
"""

from fastapi import HTTPException
from typing import List, Optional
from datetime import datetime
from core.use_cases.get_articles_use_case import GetArticlesUseCase
from core.use_cases.parse_news_use_case import ParseNewsUseCase
from core.use_cases.get_stats_use_case import GetStatsUseCase
from infrastructure.api.schemas import (
    ArticleResponse, StatsResponse, ParseResponse, 
    HealthResponse, ErrorResponse
)


class ArticleController:
    """Контроллер для работы со статьями."""

    def __init__(self, get_articles_use_case: GetArticlesUseCase):
        self.get_articles_use_case = get_articles_use_case

    async def get_articles(self, limit: int = 10, source: Optional[str] = None) -> List[ArticleResponse]:
        """Получает статьи."""
        try:
            articles = await self.get_articles_use_case.execute(limit, source)
            return [
                ArticleResponse(
                    id=article.id,
                    source=article.source,
                    title=article.title,
                    author=article.author,
                    category=article.category,
                    published=article.published.isoformat() if article.published else None,
                    created_at=article.created_at.isoformat(),
                    word_count=article.word_count,
                    reading_time=article.reading_time,
                    is_processed=article.is_processed,
                    link=article.link,
                    image_url=article.image_url,
                    summary=article.summary,
                    content=article.content
                )
                for article in articles
            ]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ошибка получения статей: {str(e)}")


class ParsingController:
    """Контроллер для парсинга новостей."""

    def __init__(self, parse_news_use_case: ParseNewsUseCase):
        self.parse_news_use_case = parse_news_use_case

    async def parse_all(self) -> ParseResponse:
        """Парсит все источники."""
        try:
            result = await self.parse_news_use_case.execute("all")
            return ParseResponse(
                message="Парсинг завершен успешно",
                new_articles_count=result.get('total', 0),
                timestamp=datetime.now().isoformat(),
                details=result
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ошибка парсинга: {str(e)}")

    async def parse_rss(self) -> ParseResponse:
        """Парсит только RSS ленты."""
        try:
            result = await self.parse_news_use_case.execute("rss")
            return ParseResponse(
                message="RSS парсинг завершен успешно",
                new_articles_count=result.get('rss', 0),
                timestamp=datetime.now().isoformat(),
                details=result
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ошибка RSS парсинга: {str(e)}")

    async def parse_telegram(self) -> ParseResponse:
        """Парсит только Telegram каналы."""
        try:
            result = await self.parse_news_use_case.execute("telegram")
            return ParseResponse(
                message="Telegram парсинг завершен успешно",
                new_articles_count=result.get('telegram', 0),
                timestamp=datetime.now().isoformat(),
                details=result
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ошибка Telegram парсинга: {str(e)}")


class StatsController:
    """Контроллер для статистики."""

    def __init__(self, get_stats_use_case: GetStatsUseCase):
        self.get_stats_use_case = get_stats_use_case

    async def get_stats(self) -> StatsResponse:
        """Получает статистику."""
        try:
            stats = await self.get_stats_use_case.execute()
            return StatsResponse(**stats)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ошибка получения статистики: {str(e)}")

    async def get_health(self) -> HealthResponse:
        """Проверка здоровья приложения."""
        try:
            stats = await self.get_stats_use_case.execute()
            return HealthResponse(
                status="healthy",
                timestamp=datetime.now().isoformat(),
                parsing_status=stats
            )
        except Exception as e:
            return HealthResponse(
                status="unhealthy",
                timestamp=datetime.now().isoformat(),
                parsing_status={"error": str(e)}
            )

