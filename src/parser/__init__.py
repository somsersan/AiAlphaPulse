"""
Модуль парсинга новостей
Содержит парсеры для различных источников новостей
"""
from .rss_parser import RSSParser
from .telegram_parser import TelegramParser

__all__ = [
    'RSSParser',
    'TelegramParser'
]
