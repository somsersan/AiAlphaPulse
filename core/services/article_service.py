"""
Сервис для работы со статьями.
Содержит бизнес-логику обработки статей.
"""

from typing import List, Optional
from core.domain.entities import Article, SourceType
from core.domain.exceptions import ArticleNotFoundError, InvalidArticleError
from core.repositories.article_repository import ArticleRepository
from core.domain.value_objects import WordCount, ReadingTime


class ArticleService:
    """Сервис для работы со статьями."""

    def __init__(self, article_repository: ArticleRepository):
        self.article_repository = article_repository

    async def create_article(self, article_data: dict) -> Article:
        """Создает новую статью с валидацией."""
        # Проверяем, не существует ли уже статья с таким заголовком
        existing_article = await self.article_repository.get_by_title(article_data['title'])
        if existing_article:
            raise InvalidArticleError(f"Article with title '{article_data['title']}' already exists")

        # Создаем доменную сущность
        article = Article(
            id=None,
            title=article_data['title'],
            link=article_data['link'],
            published=article_data.get('published'),
            summary=article_data.get('summary'),
            source=article_data['source'],
            feed_url=article_data['feed_url'],
            content=article_data.get('content'),
            author=article_data.get('author'),
            category=article_data.get('category'),
            image_url=article_data.get('image_url'),
            word_count=article_data.get('word_count', 0),
            reading_time=article_data.get('reading_time', 0),
            is_processed=article_data.get('is_processed', False),
            created_at=article_data.get('created_at'),
            source_type=SourceType(article_data.get('source_type', 'rss'))
        )

        # Пересчитываем статистику чтения
        article.calculate_reading_stats()

        return await self.article_repository.create(article)

    async def get_article_by_id(self, article_id: int) -> Article:
        """Получает статью по ID."""
        article = await self.article_repository.get_by_id(article_id)
        if not article:
            raise ArticleNotFoundError(f"Article with ID {article_id} not found")
        return article

    async def get_latest_articles(self, limit: int = 10) -> List[Article]:
        """Получает последние статьи."""
        return await self.article_repository.get_latest(limit)

    async def get_articles_by_source(self, source: str, limit: int = 10) -> List[Article]:
        """Получает статьи по источнику."""
        return await self.article_repository.get_by_source(source, limit)

    async def get_financial_articles(self, limit: int = 10) -> List[Article]:
        """Получает финансовые статьи."""
        all_articles = await self.article_repository.get_latest(limit * 2)  # Берем больше для фильтрации
        financial_articles = [article for article in all_articles if article.is_financial_news]
        return financial_articles[:limit]

    async def search_articles(self, query: str, limit: int = 10) -> List[Article]:
        """Поиск статей по тексту."""
        return await self.article_repository.search(query, limit)

    async def mark_as_processed(self, article_id: int) -> Article:
        """Отмечает статью как обработанную."""
        article = await self.get_article_by_id(article_id)
        article.is_processed = True
        return await self.article_repository.update(article)

    async def get_processing_stats(self) -> dict:
        """Получает статистику обработки статей."""
        stats = await self.article_repository.get_stats()
        return {
            'total_articles': stats.total_articles,
            'processed_articles': stats.processed_articles,
            'processing_rate': stats.processing_rate,
            'avg_words': stats.avg_words,
            'sources': stats.sources,
            'last_run': stats.last_run,
            'is_running': stats.is_running
        }
