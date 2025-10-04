"""
SQLAlchemy модели для базы данных.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from datetime import datetime

Base = declarative_base()


class ArticleModel(Base):
    """SQLAlchemy модель для статей."""
    __tablename__ = 'articles'
    
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False, unique=True)
    link = Column(String, nullable=False)
    published = Column(DateTime)
    summary = Column(Text)
    source = Column(String)
    feed_url = Column(String)
    content = Column(Text)
    author = Column(String)
    category = Column(String)
    image_url = Column(String)
    word_count = Column(Integer, default=0)
    reading_time = Column(Integer, default=0)
    is_processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<ArticleModel(title='{self.title[:30]}...', source='{self.source}')>"


class RSSFeedModel(Base):
    """SQLAlchemy модель для RSS лент."""
    __tablename__ = 'rss_feeds'
    
    id = Column(Integer, primary_key=True)
    url = Column(String, nullable=False, unique=True)
    title = Column(String)
    is_active = Column(Boolean, default=True)
    last_parsed = Column(DateTime)
    error_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<RSSFeedModel(url='{self.url}', active={self.is_active})>"


class TelegramChannelModel(Base):
    """SQLAlchemy модель для Telegram каналов."""
    __tablename__ = 'telegram_channels'
    
    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False, unique=True)
    display_name = Column(String)
    is_active = Column(Boolean, default=True)
    last_parsed = Column(DateTime)
    error_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<TelegramChannelModel(username='{self.username}', active={self.is_active})>"
