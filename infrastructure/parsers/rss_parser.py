"""
RSS парсер.
"""

import feedparser
import requests
import asyncio
import time
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from datetime import datetime
from core.domain.exceptions import RSSFeedError
from config.settings import settings


class RSSParser:
    """Парсер RSS лент."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    async def parse_feed(self, feed_url: str) -> List[Dict[str, Any]]:
        """Парсит RSS ленту."""
        try:
            # Парсим RSS ленту
            feed = feedparser.parse(feed_url)
            
            if feed.bozo:
                print(f"⚠️ Предупреждение: RSS-лента {feed_url} может содержать ошибки")
                print(f"📋 Детали ошибки: {feed.bozo_exception}")
            
            if not hasattr(feed, 'entries') or not feed.entries:
                print(f"❌ Лента {feed_url} пуста или не содержит записей")
                return []
            
            articles = []
            feed_title = feed.feed.title if hasattr(feed.feed, 'title') else 'Неизвестный источник'
            
            for entry in feed.entries:
                try:
                    article_data = await self._parse_entry(entry, feed_title, feed_url)
                    if article_data:
                        articles.append(article_data)
                    
                    # Небольшая пауза между запросами
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    print(f"❌ Ошибка при обработке статьи: {e}")
                    continue
            
            print(f"✅ RSS лента {feed_title}: обработано {len(articles)} статей")
            return articles
            
        except Exception as e:
            raise RSSFeedError(f"Ошибка парсинга RSS ленты {feed_url}: {str(e)}")

    async def _parse_entry(self, entry, feed_title: str, feed_url: str) -> Dict[str, Any]:
        """Парсит отдельную запись RSS."""
        # Извлекаем базовую информацию
        pub_date = None
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            pub_date = datetime(*entry.published_parsed[:6])
        
        # Извлекаем дополнительные метаданные
        metadata = self._extract_article_metadata(entry)
        
        # Извлекаем полный контент
        full_content = await self._extract_full_content(entry.link)
        
        # Вычисляем статистику
        word_count, reading_time = self._calculate_reading_stats(full_content)
        
        return {
            'title': entry.title,
            'link': entry.link,
            'published': pub_date,
            'summary': entry.summary if hasattr(entry, 'summary') else 'Нет описания',
            'source': feed_title,
            'feed_url': feed_url,
            'content': full_content,
            'author': metadata['author'],
            'category': metadata['category'],
            'image_url': metadata['image_url'],
            'word_count': word_count,
            'reading_time': reading_time,
            'is_processed': True,
            'created_at': datetime.now()
        }

    def _extract_article_metadata(self, entry) -> Dict[str, Any]:
        """Извлекает дополнительные метаданные из RSS-записи."""
        metadata = {
            'author': None,
            'category': None,
            'image_url': None
        }
        
        # Автор
        if hasattr(entry, 'author'):
            metadata['author'] = entry.author
        elif hasattr(entry, 'author_detail') and hasattr(entry.author_detail, 'name'):
            metadata['author'] = entry.author_detail.name
        
        # Категория/теги
        if hasattr(entry, 'tags') and entry.tags:
            categories = [tag.term for tag in entry.tags if hasattr(tag, 'term')]
            metadata['category'] = ', '.join(categories[:3])
        
        # Изображение
        if hasattr(entry, 'media_content') and entry.media_content:
            for media in entry.media_content:
                if hasattr(media, 'type') and 'image' in media.type:
                    metadata['image_url'] = media.url
                    break
        
        # Альтернативные способы поиска изображения
        if not metadata['image_url'] and hasattr(entry, 'enclosures'):
            for enclosure in entry.enclosures:
                if hasattr(enclosure, 'type') and 'image' in enclosure.type:
                    metadata['image_url'] = enclosure.href
                    break
        
        return metadata

    async def _extract_full_content(self, article_url: str, max_retries: int = 3) -> str:
        """Извлекает полный текст статьи по URL."""
        for attempt in range(max_retries):
            try:
                response = self.session.get(article_url, timeout=settings.parsing.timeout)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Удаляем ненужные элементы
                for script in soup(["script", "style", "nav", "footer", "aside"]):
                    script.decompose()
                
                # Ищем основной контент по различным селекторам
                content_selectors = [
                    'article', '.article-content', '.post-content', '.entry-content',
                    '.content', '.main-content', '.story-content', '.news-content',
                    '[role="main"]', '.article-body', '.post-body'
                ]
                
                content = None
                for selector in content_selectors:
                    content_elem = soup.select_one(selector)
                    if content_elem:
                        content = content_elem.get_text(strip=True)
                        break
                
                if not content:
                    # Если не нашли специальный контейнер, берем body
                    body = soup.find('body')
                    if body:
                        content = body.get_text(strip=True)
                
                return content[:5000] if content else None  # Ограничиваем размер
                
            except Exception as e:
                print(f"⚠️ Ошибка при извлечении контента (попытка {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)  # Пауза перед повтором
                continue
        
        return None

    def _calculate_reading_stats(self, content: str) -> tuple[int, int]:
        """Вычисляет статистику чтения."""
        if not content:
            return 0, 0
        
        # Подсчет слов (простая логика)
        import re
        words = re.findall(r'\b\w+\b', content.lower())
        word_count = len(words)
        
        # Время чтения (примерно 200 слов в минуту)
        reading_time = max(1, word_count // settings.parsing.words_per_minute)
        
        return word_count, reading_time
