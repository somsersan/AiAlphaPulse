"""
Use Case для парсинга новостей.
"""

from typing import Dict, Any
from core.services.parsing_service import ParsingService


class ParseNewsUseCase:
    """Use Case для парсинга новостей."""

    def __init__(self, parsing_service: ParsingService):
        self.parsing_service = parsing_service

    async def execute(self, source_type: str = "all") -> Dict[str, Any]:
        """Выполняет парсинг новостей."""
        if source_type == "rss":
            count = await self.parsing_service.parse_rss_feeds()
            return {"rss": count, "total": count}
        elif source_type == "telegram":
            count = await self.parsing_service.parse_telegram_channels()
            return {"telegram": count, "total": count}
        else:
            return await self.parsing_service.parse_all_sources()
