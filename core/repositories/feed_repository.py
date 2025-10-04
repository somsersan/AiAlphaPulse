"""
Интерфейс репозитория для работы с RSS лентами и Telegram каналами.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from core.domain.entities import RSSFeed, TelegramChannel


class FeedRepository(ABC):
    """Абстрактный репозиторий для работы с лентами."""

    @abstractmethod
    async def get_active_rss_feeds(self) -> List[RSSFeed]:
        """Получает активные RSS ленты."""
        pass

    @abstractmethod
    async def get_active_telegram_channels(self) -> List[TelegramChannel]:
        """Получает активные Telegram каналы."""
        pass

    @abstractmethod
    async def update_feed_last_parsed(self, feed_url: str) -> None:
        """Обновляет время последнего парсинга ленты."""
        pass

    @abstractmethod
    async def increment_feed_error_count(self, feed_url: str) -> None:
        """Увеличивает счетчик ошибок ленты."""
        pass

    @abstractmethod
    async def reset_feed_error_count(self, feed_url: str) -> None:
        """Сбрасывает счетчик ошибок ленты."""
        pass
