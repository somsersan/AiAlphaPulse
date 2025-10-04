"""
Use Case для получения статистики.
"""

from typing import Dict, Any
from core.services.article_service import ArticleService


class GetStatsUseCase:
    """Use Case для получения статистики."""

    def __init__(self, article_service: ArticleService):
        self.article_service = article_service

    async def execute(self) -> Dict[str, Any]:
        """Выполняет получение статистики."""
        return await self.article_service.get_processing_stats()
