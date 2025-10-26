"""
Реализации репозиториев для работы с базой данных.
"""

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from core.domain.entities import Article, ParsingStats, RSSFeed, TelegramChannel
from core.repositories.article_repository import ArticleRepository
from core.repositories.feed_repository import FeedRepository
from infrastructure.database.models import ArticleModel, RSSFeedModel, TelegramChannelModel
from infrastructure.database.connection import db_connection


class SQLArticleRepository(ArticleRepository):
    """SQLAlchemy реализация репозитория статей."""

    def __init__(self):
        self.db = db_connection

    def _model_to_entity(self, model: ArticleModel) -> Article:
        """Преобразует SQLAlchemy модель в доменную сущность."""
        return Article(
            id=model.id,
            title=model.title,
            link=model.link,
            published=model.published,
            summary=model.summary,
            source=model.source,
            feed_url=model.feed_url,
            content=model.content,
            author=model.author,
            category=model.category,
            image_url=model.image_url,
            word_count=model.word_count,
            reading_time=model.reading_time,
            is_processed=model.is_processed,
            created_at=model.created_at
        )

    def _entity_to_model(self, entity: Article) -> ArticleModel:
        """Преобразует доменную сущность в SQLAlchemy модель."""
        return ArticleModel(
            id=entity.id,
            title=entity.title,
            link=entity.link,
            published=entity.published,
            summary=entity.summary,
            source=entity.source,
            feed_url=entity.feed_url,
            content=entity.content,
            author=entity.author,
            category=entity.category,
            image_url=entity.image_url,
            word_count=entity.word_count,
            reading_time=entity.reading_time,
            is_processed=entity.is_processed,
            created_at=entity.created_at
        )

    async def create(self, article: Article) -> Article:
        """Создает новую статью."""
        session = self.db.get_session()
        try:
            model = self._entity_to_model(article)
            session.add(model)
            session.commit()
            session.refresh(model)
            return self._model_to_entity(model)
        finally:
            session.close()

    async def get_by_id(self, article_id: int) -> Optional[Article]:
        """Получает статью по ID."""
        session = self.db.get_session()
        try:
            model = session.query(ArticleModel).filter(ArticleModel.id == article_id).first()
            return self._model_to_entity(model) if model else None
        finally:
            session.close()

    async def get_by_title(self, title: str) -> Optional[Article]:
        """Получает статью по заголовку."""
        session = self.db.get_session()
        try:
            model = session.query(ArticleModel).filter(ArticleModel.title == title).first()
            return self._model_to_entity(model) if model else None
        finally:
            session.close()

    async def get_latest(self, limit: int = 10) -> List[Article]:
        """Получает последние статьи."""
        session = self.db.get_session()
        try:
            models = session.query(ArticleModel).order_by(ArticleModel.id.desc()).limit(limit).all()
            return [self._model_to_entity(model) for model in models]
        finally:
            session.close()

    async def get_by_source(self, source: str, limit: int = 10) -> List[Article]:
        """Получает статьи по источнику."""
        session = self.db.get_session()
        try:
            models = session.query(ArticleModel).filter(ArticleModel.source == source).order_by(ArticleModel.id.desc()).limit(limit).all()
            return [self._model_to_entity(model) for model in models]
        finally:
            session.close()

    async def get_unprocessed(self, limit: int = 10) -> List[Article]:
        """Получает необработанные статьи."""
        session = self.db.get_session()
        try:
            models = session.query(ArticleModel).filter(ArticleModel.is_processed == False).order_by(ArticleModel.id.desc()).limit(limit).all()
            return [self._model_to_entity(model) for model in models]
        finally:
            session.close()

    async def update(self, article: Article) -> Article:
        """Обновляет статью."""
        session = self.db.get_session()
        try:
            model = session.query(ArticleModel).filter(ArticleModel.id == article.id).first()
            if not model:
                raise ValueError(f"Article with ID {article.id} not found")
            
            # Обновляем поля
            for field in ['title', 'link', 'published', 'summary', 'source', 'feed_url', 
                         'content', 'author', 'category', 'image_url', 'word_count', 
                         'reading_time', 'is_processed']:
                setattr(model, field, getattr(article, field))
            
            session.commit()
            session.refresh(model)
            return self._model_to_entity(model)
        finally:
            session.close()

    async def delete(self, article_id: int) -> bool:
        """Удаляет статью."""
        session = self.db.get_session()
        try:
            model = session.query(ArticleModel).filter(ArticleModel.id == article_id).first()
            if not model:
                return False
            
            session.delete(model)
            session.commit()
            return True
        finally:
            session.close()

    async def get_stats(self) -> ParsingStats:
        """Получает статистику по статьям."""
        session = self.db.get_session()
        try:
            total_articles = session.query(ArticleModel).count()
            processed_articles = session.query(ArticleModel).filter(ArticleModel.is_processed == True).count()
            
            # Статистика по источникам
            sources_query = session.query(ArticleModel.source, session.query(ArticleModel).filter(ArticleModel.source == ArticleModel.source).count()).group_by(ArticleModel.source).all()
            sources = [{'source': source, 'count': count} for source, count in sources_query]
            
            # Средняя статистика
            avg_words_query = session.query(ArticleModel.word_count).filter(ArticleModel.word_count.isnot(None)).all()
            avg_words = sum([w[0] for w in avg_words_query]) / len(avg_words_query) if avg_words_query else 0
            
            return ParsingStats(
                total_articles=total_articles,
                processed_articles=processed_articles,
                avg_words=round(avg_words, 0),
                sources=sources
            )
        finally:
            session.close()

    async def exists_by_title(self, title: str) -> bool:
        """Проверяет, существует ли статья с таким заголовком."""
        session = self.db.get_session()
        try:
            return session.query(ArticleModel).filter(ArticleModel.title == title).first() is not None
        finally:
            session.close()

    async def search(self, query: str, limit: int = 10) -> List[Article]:
        """Поиск статей по тексту."""
        session = self.db.get_session()
        try:
            models = session.query(ArticleModel).filter(
                ArticleModel.title.contains(query) | 
                ArticleModel.content.contains(query) |
                ArticleModel.summary.contains(query)
            ).order_by(ArticleModel.id.desc()).limit(limit).all()
            return [self._model_to_entity(model) for model in models]
        finally:
            session.close()


class SQLFeedRepository(FeedRepository):
    """SQLAlchemy реализация репозитория лент."""

    def __init__(self):
        self.db = db_connection

    async def get_active_rss_feeds(self) -> List[RSSFeed]:
        """Получает активные RSS ленты."""
        session = self.db.get_session()
        try:
            models = session.query(RSSFeedModel).filter(RSSFeedModel.is_active == True).all()
            return [
                RSSFeed(
                    url=model.url,
                    title=model.title or "",
                    is_active=model.is_active,
                    last_parsed=model.last_parsed,
                    error_count=model.error_count
                )
                for model in models
            ]
        finally:
            session.close()

    async def get_active_telegram_channels(self) -> List[TelegramChannel]:
        """Получает активные Telegram каналы."""
        session = self.db.get_session()
        try:
            models = session.query(TelegramChannelModel).filter(TelegramChannelModel.is_active == True).all()
            return [
                TelegramChannel(
                    username=model.username,
                    display_name=model.display_name or "",
                    is_active=model.is_active,
                    last_parsed=model.last_parsed,
                    error_count=model.error_count
                )
                for model in models
            ]
        finally:
            session.close()

    async def update_feed_last_parsed(self, feed_url: str) -> None:
        """Обновляет время последнего парсинга ленты."""
        session = self.db.get_session()
        try:
            # Пробуем обновить RSS ленту
            rss_model = session.query(RSSFeedModel).filter(RSSFeedModel.url == feed_url).first()
            if rss_model:
                rss_model.last_parsed = datetime.now()
                session.commit()
                return
            
            # Пробуем обновить Telegram канал
            telegram_model = session.query(TelegramChannelModel).filter(TelegramChannelModel.username == feed_url).first()
            if telegram_model:
                telegram_model.last_parsed = datetime.now()
                session.commit()
        finally:
            session.close()

    async def increment_feed_error_count(self, feed_url: str) -> None:
        """Увеличивает счетчик ошибок ленты."""
        session = self.db.get_session()
        try:
            # Пробуем обновить RSS ленту
            rss_model = session.query(RSSFeedModel).filter(RSSFeedModel.url == feed_url).first()
            if rss_model:
                rss_model.error_count += 1
                session.commit()
                return
            
            # Пробуем обновить Telegram канал
            telegram_model = session.query(TelegramChannelModel).filter(TelegramChannelModel.username == feed_url).first()
            if telegram_model:
                telegram_model.error_count += 1
                session.commit()
        finally:
            session.close()

    async def reset_feed_error_count(self, feed_url: str) -> None:
        """Сбрасывает счетчик ошибок ленты."""
        session = self.db.get_session()
        try:
            # Пробуем обновить RSS ленту
            rss_model = session.query(RSSFeedModel).filter(RSSFeedModel.url == feed_url).first()
            if rss_model:
                rss_model.error_count = 0
                session.commit()
                return
            
            # Пробуем обновить Telegram канал
            telegram_model = session.query(TelegramChannelModel).filter(TelegramChannelModel.username == feed_url).first()
            if telegram_model:
                telegram_model.error_count = 0
                session.commit()
        finally:
            session.close()

