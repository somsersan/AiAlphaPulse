"""
Сервис для парсинга новостей.
Координирует процесс парсинга различных источников.
"""

import asyncio
from typing import List, Dict, Any
from datetime import datetime
from core.domain.entities import Article, SourceType, ParsingStats
from core.domain.exceptions import ParsingError
from core.repositories.article_repository import ArticleRepository
from core.repositories.feed_repository import FeedRepository


class ParsingService:
    """Сервис для парсинга новостей."""

    def __init__(
        self, 
        article_repository: ArticleRepository,
        feed_repository: FeedRepository,
        rss_parser: 'RSSParser',
        telegram_parser: 'TelegramParser'
    ):
        self.article_repository = article_repository
        self.feed_repository = feed_repository
        self.rss_parser = rss_parser
        self.telegram_parser = telegram_parser
        self._is_running = False

    @property
    def is_running(self) -> bool:
        """Проверяет, выполняется ли парсинг."""
        return self._is_running

    async def parse_all_sources(self) -> Dict[str, int]:
        """Парсит все источники новостей."""
        if self._is_running:
            raise ParsingError("Parsing is already running")

        self._is_running = True
        results = {}

        try:
            # Парсинг RSS лент
            rss_count = await self.parse_rss_feeds()
            results['rss'] = rss_count

            # Парсинг Telegram каналов
            telegram_count = await self.parse_telegram_channels()
            results['telegram'] = telegram_count

            results['total'] = rss_count + telegram_count
            return results

        except Exception as e:
            raise ParsingError(f"Error during parsing: {str(e)}")
        finally:
            self._is_running = False

    async def parse_rss_feeds(self) -> int:
        """Парсит RSS ленты."""
        feeds = await self.feed_repository.get_active_rss_feeds()
        total_new_articles = 0

        for feed in feeds:
            try:
                articles = await self.rss_parser.parse_feed(feed.url)
                new_articles = await self._save_articles(articles, SourceType.RSS)
                total_new_articles += new_articles
                
                # Обновляем время последнего парсинга
                await self.feed_repository.update_feed_last_parsed(feed.url)
                await self.feed_repository.reset_feed_error_count(feed.url)

            except Exception as e:
                # Увеличиваем счетчик ошибок
                await self.feed_repository.increment_feed_error_count(feed.url)
                print(f"Error parsing RSS feed {feed.url}: {e}")

        return total_new_articles

    async def parse_telegram_channels(self) -> int:
        """Парсит Telegram каналы."""
        channels = await self.feed_repository.get_active_telegram_channels()
        total_new_articles = 0

        for channel in channels:
            try:
                articles = await self.telegram_parser.parse_channel(channel.username)
                new_articles = await self._save_articles(articles, SourceType.TELEGRAM)
                total_new_articles += new_articles
                
                # Обновляем время последнего парсинга
                await self.feed_repository.update_feed_last_parsed(channel.username)
                await self.feed_repository.reset_feed_error_count(channel.username)

            except Exception as e:
                # Увеличиваем счетчик ошибок
                await self.feed_repository.increment_feed_error_count(channel.username)
                print(f"Error parsing Telegram channel {channel.username}: {e}")

        return total_new_articles

    async def _save_articles(self, articles: List[Dict[str, Any]], source_type: SourceType) -> int:
        """Сохраняет статьи в базу данных."""
        new_articles_count = 0

        for article_data in articles:
            try:
                # Проверяем, не существует ли уже статья
                exists = await self.article_repository.exists_by_title(article_data['title'])
                if exists:
                    continue

                # Создаем статью через сервис
                from core.services.article_service import ArticleService
                article_service = ArticleService(self.article_repository)
                await article_service.create_article(article_data)
                new_articles_count += 1

            except Exception as e:
                print(f"Error saving article: {e}")
                continue

        return new_articles_count

    async def get_parsing_status(self) -> Dict[str, Any]:
        """Получает статус парсинга."""
        stats = await self.article_repository.get_stats()
        return {
            'is_running': self._is_running,
            'last_run': stats.last_run,
            'total_articles': stats.total_articles,
            'processed_articles': stats.processed_articles,
            'processing_rate': stats.processing_rate
        }
