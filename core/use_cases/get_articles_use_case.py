"""
Use Case для получения статей.
"""

from typing import List, Optional
from core.domain.entities import Article
from core.services.article_service import ArticleService


class GetArticlesUseCase:
    """Use Case для получения статей."""

    def __init__(self, article_service: ArticleService):
        self.article_service = article_service

    async def execute(self, limit: int = 10, source: Optional[str] = None) -> List[Article]:
        """Выполняет получение статей."""
        if source:
            return await self.article_service.get_articles_by_source(source, limit)
        return await self.article_service.get_latest_articles(limit)
