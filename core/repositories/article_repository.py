"""
Интерфейс репозитория для работы со статьями.
Определяет контракт для работы с данными статей.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from core.domain.entities import Article, ParsingStats


class ArticleRepository(ABC):
    """Абстрактный репозиторий для работы со статьями."""

    @abstractmethod
    async def create(self, article: Article) -> Article:
        """Создает новую статью."""
        pass

    @abstractmethod
    async def get_by_id(self, article_id: int) -> Optional[Article]:
        """Получает статью по ID."""
        pass

    @abstractmethod
    async def get_by_title(self, title: str) -> Optional[Article]:
        """Получает статью по заголовку."""
        pass

    @abstractmethod
    async def get_latest(self, limit: int = 10) -> List[Article]:
        """Получает последние статьи."""
        pass

    @abstractmethod
    async def get_by_source(self, source: str, limit: int = 10) -> List[Article]:
        """Получает статьи по источнику."""
        pass

    @abstractmethod
    async def get_unprocessed(self, limit: int = 10) -> List[Article]:
        """Получает необработанные статьи."""
        pass

    @abstractmethod
    async def update(self, article: Article) -> Article:
        """Обновляет статью."""
        pass

    @abstractmethod
    async def delete(self, article_id: int) -> bool:
        """Удаляет статью."""
        pass

    @abstractmethod
    async def get_stats(self) -> ParsingStats:
        """Получает статистику по статьям."""
        pass

    @abstractmethod
    async def exists_by_title(self, title: str) -> bool:
        """Проверяет, существует ли статья с таким заголовком."""
        pass

    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> List[Article]:
        """Поиск статей по тексту."""
        pass
