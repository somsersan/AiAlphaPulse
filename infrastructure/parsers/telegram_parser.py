"""
Telegram парсер.
"""

import asyncio
import httpx
import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from datetime import datetime
from core.domain.exceptions import TelegramChannelError
from config.settings import settings


class TelegramParser:
    """Парсер Telegram каналов."""

    def __init__(self):
        self.client = httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            follow_redirects=False,
            timeout=settings.parsing.timeout
        )

    async def parse_channel(self, channel_username: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Парсит Telegram канал."""
        try:
            # Убираем @ если есть
            if channel_username.startswith('@'):
                channel_username = channel_username[1:]
            
            url = f"https://t.me/s/{channel_username}"
            posts = []

            resp = await self.client.get(url)
            if resp.status_code == 302:
                print(f"⚠️ Пропускаем @{channel_username} → редирект")
                return []

            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            messages = soup.find_all("div", class_="tgme_widget_message", limit=limit)

            for msg in messages:
                post_data = self._parse_message(msg, channel_username)
                if post_data:
                    posts.append(post_data)

            print(f"✅ Telegram канал @{channel_username}: обработано {len(posts)} постов")
            return posts

        except Exception as e:
            raise TelegramChannelError(f"Ошибка парсинга Telegram канала @{channel_username}: {str(e)}")

    def _parse_message(self, msg, channel_username: str) -> Dict[str, Any]:
        """Парсит отдельное сообщение Telegram."""
        try:
            text_div = msg.find("div", class_="tgme_widget_message_text")
            text = text_div.get_text(strip=True) if text_div else ""
            
            if len(text) < 10:
                return None

            time_elem = msg.find("time")
            date_str = time_elem["datetime"] if time_elem and time_elem.has_attr("datetime") else datetime.now().isoformat()

            link = msg.get("data-post", "")
            post_id = link.split("/")[-1] if link else "unknown"

            views_elem = msg.find("span", class_="tgme_widget_message_views")
            views = views_elem.get_text(strip=True) if views_elem else "0"

            categories = self._categorize(text)

            # Парсим дату
            pub_date = None
            try:
                pub_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            except:
                pub_date = datetime.now()

            # Вычисляем статистику
            word_count, reading_time = self._calculate_reading_stats(text)

            return {
                'title': text[:255],  # Ограничиваем длину заголовка
                'link': f"https://t.me/{channel_username}/{post_id}",
                'published': pub_date,
                'summary': text[:500],  # Первые 500 символов как summary
                'source': f"@{channel_username}",
                'feed_url': f"https://t.me/{channel_username}",
                'content': text,
                'author': None,  # В Telegram постах обычно нет автора
                'category': ", ".join(categories),
                'image_url': None,  # Пока не извлекаем изображения
                'word_count': word_count,
                'reading_time': reading_time,
                'is_processed': True,
                'created_at': datetime.now()
            }

        except Exception as e:
            print(f"⚠️ Ошибка парсинга поста @{channel_username}: {e}")
            return None

    def _categorize(self, text: str) -> List[str]:
        """Категоризирует текст по ключевым словам."""
        keywords = {
            "акцизы": r"(акциз|табак|алкоголь|топливо|бензин|сигарет)",
            "акции": r"(акци|бирж|торг|котировк|индекс|мосбирж|ммвб|ipo|дивиденд)",
            "мировая экономика": r"(доллар|евро|курс|нефть|золото|экспорт|импорт|санкци|опек|фрс|fed)",
        }
        
        text_lower = text.lower()
        categories = [cat for cat, pattern in keywords.items() if re.search(pattern, text_lower)]
        categories.append("все новости")
        return categories

    def _calculate_reading_stats(self, content: str) -> tuple[int, int]:
        """Вычисляет статистику чтения."""
        if not content:
            return 0, 0
        
        # Подсчет слов (простая логика)
        words = re.findall(r'\b\w+\b', content.lower())
        word_count = len(words)
        
        # Время чтения (примерно 200 слов в минуту)
        reading_time = max(1, word_count // settings.parsing.words_per_minute)
        
        return word_count, reading_time

    async def close(self):
        """Закрывает HTTP клиент."""
        await self.client.aclose()

