"""
Инициализатор лент и каналов.
"""

from typing import List
from core.domain.entities import RSSFeed, TelegramChannel
from infrastructure.database.models import RSSFeedModel, TelegramChannelModel
from infrastructure.database.connection import db_connection
from config.settings import settings


class FeedInitializer:
    """Инициализирует RSS ленты и Telegram каналы в базе данных."""

    def __init__(self):
        self.db = db_connection

    async def initialize_feeds(self):
        """Инициализирует все ленты и каналы."""
        await self._initialize_rss_feeds()
        await self._initialize_telegram_channels()

    async def _initialize_rss_feeds(self):
        """Инициализирует RSS ленты."""
        session = self.db.get_session()
        try:
            for url in settings.rss.urls:
                # Проверяем, существует ли уже лента
                existing = session.query(RSSFeedModel).filter(RSSFeedModel.url == url).first()
                if not existing:
                    feed = RSSFeedModel(
                        url=url,
                        title=f"RSS Feed {url}",
                        is_active=True
                    )
                    session.add(feed)
                    print(f"✅ Добавлена RSS лента: {url}")
                else:
                    print(f"ℹ️ RSS лента уже существует: {url}")
            
            session.commit()
        finally:
            session.close()

    async def _initialize_telegram_channels(self):
        """Инициализирует Telegram каналы."""
        session = self.db.get_session()
        try:
            for username in settings.telegram.channels:
                # Убираем @ если есть
                if username.startswith('@'):
                    username = username[1:]
                
                # Проверяем, существует ли уже канал
                existing = session.query(TelegramChannelModel).filter(TelegramChannelModel.username == f"@{username}").first()
                if not existing:
                    channel = TelegramChannelModel(
                        username=f"@{username}",
                        display_name=username,
                        is_active=True
                    )
                    session.add(channel)
                    print(f"✅ Добавлен Telegram канал: @{username}")
                else:
                    print(f"ℹ️ Telegram канал уже существует: @{username}")
            
            session.commit()
        finally:
            session.close()
