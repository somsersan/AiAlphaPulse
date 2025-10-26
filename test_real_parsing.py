"""
Тест реального парсинга с базой данных.
"""

import asyncio
import sys
import os

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from infrastructure.database.repositories import SQLArticleRepository, SQLFeedRepository
from infrastructure.parsers.rss_parser import RSSParser
from infrastructure.parsers.telegram_parser import TelegramParser
from infrastructure.parsers.api_parser import APIParser
from core.services.parsing_service import ParsingService


async def test_real_parsing():
    """Тестируем реальный парсинг с базой данных."""
    print("🔧 Тестирование реального парсинга...")
    
    try:
        # Создаем репозитории
        article_repo = SQLArticleRepository()
        feed_repo = SQLFeedRepository()
        
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
        
        print("📊 Начинаем парсинг всех источников...")
        
        # Парсим все источники
        results = await parsing_service.parse_all_sources()
        
        print(f"✅ Парсинг завершен!")
        print(f"📊 Результаты:")
        print(f"   - RSS: {results.get('rss', 0)} статей")
        print(f"   - Telegram: {results.get('telegram', 0)} статей")
        print(f"   - API (криптовалюты): {results.get('api', 0)} статей")
        print(f"   - Всего: {results.get('total', 0)} статей")
        
        # Получаем статистику
        stats = await parsing_service.get_parsing_status()
        print(f"\n📈 Статистика:")
        print(f"   - Всего статей в БД: {stats.get('total_articles', 0)}")
        print(f"   - Обработано: {stats.get('processed_articles', 0)}")
        print(f"   - Процент обработки: {stats.get('processing_rate', 0):.1f}%")
        
        return results.get('api', 0) > 0
        
    except Exception as e:
        print(f"❌ Ошибка при парсинге: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_api_only():
    """Тестируем только API парсинг."""
    print("🔧 Тестирование только API парсинга...")
    
    try:
        # Создаем репозитории
        article_repo = SQLArticleRepository()
        feed_repo = SQLFeedRepository()
        
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
        
        print("📊 Начинаем парсинг только API данных...")
        
        # Парсим только API
        api_count = await parsing_service.parse_api_data()
        
        print(f"✅ API парсинг завершен!")
        print(f"📰 Получено статей о криптовалютах: {api_count}")
        
        return api_count > 0
        
    except Exception as e:
        print(f"❌ Ошибка при API парсинге: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Основная функция тестирования."""
    print("=" * 60)
    print("🤖 Тестирование реального парсинга")
    print("=" * 60)
    
    # Тест 1: Только API парсинг
    print("🔧 Тест 1: Парсинг только API данных")
    api_success = await test_api_only()
    
    if api_success:
        print("\n" + "=" * 40)
        print("🔧 Тест 2: Полный парсинг всех источников")
        print("=" * 40)
        full_success = await test_real_parsing()
    else:
        print("❌ API парсинг не работает, пропускаем полный тест")
        full_success = False
    
    print("\n" + "=" * 60)
    if api_success:
        print("✅ API парсинг работает!")
        if full_success:
            print("✅ Полный парсинг работает!")
        else:
            print("⚠️ Полный парсинг требует дополнительной настройки")
    else:
        print("❌ API парсинг не работает")
        print("🔧 Проверьте настройки и зависимости")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

