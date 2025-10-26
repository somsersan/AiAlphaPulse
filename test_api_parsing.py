"""
Тест парсинга API данных через ParsingService.
"""

import asyncio
import sys
import os

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from infrastructure.parsers.api_parser import APIParser
from core.services.parsing_service import ParsingService
from infrastructure.database.repositories import SQLArticleRepository, SQLFeedRepository
from infrastructure.parsers.rss_parser import RSSParser
from infrastructure.parsers.telegram_parser import TelegramParser


class MockRepository:
    """Мок-репозиторий для тестирования."""
    
    def __init__(self):
        self.articles = []
        self.stats = {
            'total_articles': 0,
            'processed_articles': 0,
            'last_run': None,
            'processing_rate': 0.0
        }
    
    async def exists_by_title(self, title):
        """Проверяет существование статьи по заголовку."""
        return any(article.get('title') == title for article in self.articles)
    
    async def create_article(self, article_data):
        """Создает статью."""
        self.articles.append(article_data)
        self.stats['total_articles'] += 1
        print(f"📰 Создана статья: {article_data.get('title', 'Unknown')}")
        return True
    
    async def get_stats(self):
        """Возвращает статистику."""
        from core.domain.entities import ParsingStats
        return ParsingStats(
            total_articles=self.stats['total_articles'],
            processed_articles=self.stats['processed_articles'],
            avg_words=0.0,
            sources=[],
            last_run=self.stats['last_run'],
            is_running=False
        )


async def test_api_parsing():
    """Тестируем парсинг API данных."""
    print("🔧 Тестирование парсинга API данных...")
    
    try:
        # Создаем мок-репозитории
        article_repo = MockRepository()
        feed_repo = MockRepository()
        
        # Создаем парсеры
        rss_parser = RSSParser()
        telegram_parser = TelegramParser()
        api_parser = APIParser(settings.crypto)
        
        # Создаем сервис парсинга
        parsing_service = ParsingService(
            article_repository=article_repo,
            feed_repository=feed_repo,
            rss_parser=rss_parser,
            telegram_parser=telegram_parser,
            api_parser=api_parser
        )
        
        print("📊 Начинаем парсинг API данных...")
        
        # Парсим только API данные
        api_count = await parsing_service.parse_api_data()
        
        print(f"✅ Парсинг API завершен!")
        print(f"📰 Получено статей: {api_count}")
        print(f"📊 Всего статей в репозитории: {len(article_repo.articles)}")
        
        # Показываем первые несколько статей
        for i, article in enumerate(article_repo.articles[:3], 1):
            print(f"\n📰 Статья {i}:")
            print(f"   Заголовок: {article.get('title', 'Unknown')}")
            print(f"   Источник: {article.get('source', 'Unknown')}")
            print(f"   Категория: {article.get('category', 'Unknown')}")
            print(f"   Слов: {article.get('word_count', 0)}")
        
        return api_count > 0
        
    except Exception as e:
        print(f"❌ Ошибка при парсинге API: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_full_parsing():
    """Тестируем полный парсинг всех источников."""
    print("\n🔧 Тестирование полного парсинга...")
    
    try:
        # Создаем мок-репозитории
        article_repo = MockRepository()
        feed_repo = MockRepository()
        
        # Создаем парсеры
        rss_parser = RSSParser()
        telegram_parser = TelegramParser()
        api_parser = APIParser(settings.crypto)
        
        # Создаем сервис парсинга
        parsing_service = ParsingService(
            article_repository=article_repo,
            feed_repository=feed_repo,
            rss_parser=rss_parser,
            telegram_parser=telegram_parser,
            api_parser=api_parser
        )
        
        print("📊 Начинаем полный парсинг...")
        
        # Парсим все источники
        results = await parsing_service.parse_all_sources()
        
        print(f"✅ Полный парсинг завершен!")
        print(f"📊 Результаты:")
        print(f"   - RSS: {results.get('rss', 0)} статей")
        print(f"   - Telegram: {results.get('telegram', 0)} статей")
        print(f"   - API: {results.get('api', 0)} статей")
        print(f"   - Всего: {results.get('total', 0)} статей")
        
        return results.get('api', 0) > 0
        
    except Exception as e:
        print(f"❌ Ошибка при полном парсинге: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Основная функция тестирования."""
    print("=" * 60)
    print("🤖 Тестирование парсинга API данных")
    print("=" * 60)
    
    # Тест 1: Только API парсинг
    print("🔧 Тест 1: Парсинг только API данных")
    api_success = await test_api_parsing()
    
    # Тест 2: Полный парсинг
    print("\n🔧 Тест 2: Полный парсинг всех источников")
    full_success = await test_full_parsing()
    
    print("\n" + "=" * 60)
    if api_success and full_success:
        print("✅ Все тесты пройдены успешно!")
        print("🚀 API парсинг работает корректно")
    else:
        print("❌ Некоторые тесты не пройдены")
        print("🔧 Требуется дополнительная настройка")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

