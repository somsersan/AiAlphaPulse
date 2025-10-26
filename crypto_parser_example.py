"""
Пример использования APIParser для парсинга криптовалютных данных.
"""

import asyncio
import sys
import os

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from infrastructure.parsers.api_parser import APIParser
from core.services.parsing_service import ParsingService
from infrastructure.database.repositories import ArticleRepository, FeedRepository
from infrastructure.parsers.rss_parser import RSSParser
from infrastructure.parsers.telegram_parser import TelegramParser


async def main():
    """Основная функция для тестирования парсера."""
    print("🚀 Запуск парсера криптовалютных данных...")
    
    try:
        # Создаем репозитории
        article_repo = ArticleRepository()
        feed_repo = FeedRepository()
        
        # Создаем парсеры
        rss_parser = RSSParser()
        telegram_parser = TelegramParser()
        
        # Создаем API парсер с настройками криптовалют
        api_parser = APIParser(settings.crypto)
        
        # Создаем сервис парсинга
        parsing_service = ParsingService(
            article_repository=article_repo,
            feed_repository=feed_repo,
            rss_parser=rss_parser,
            telegram_parser=telegram_parser,
            api_parser=api_parser
        )
        
        print("📊 Начинаем парсинг криптовалютных данных...")
        
        # Используем async context manager для APIParser
        async with api_parser:
            # Парсим только API данные
            api_count = await parsing_service.parse_api_data()
            print(f"✅ Получено {api_count} новых статей о криптовалютах")
        
        # Получаем общую статистику
        stats = await parsing_service.get_parsing_status()
        print(f"📈 Общая статистика:")
        print(f"   - Всего статей: {stats.get('total_articles', 0)}")
        print(f"   - Обработано: {stats.get('processed_articles', 0)}")
        print(f"   - Процент обработки: {stats.get('processing_rate', 0):.1f}%")
        
    except Exception as e:
        print(f"❌ Ошибка при парсинге: {e}")
        import traceback
        traceback.print_exc()


async def test_api_parser_directly():
    """Прямое тестирование APIParser без сервиса."""
    print("🔧 Прямое тестирование APIParser...")
    
    try:
        # Создаем парсер
        api_parser = APIParser(settings.crypto)
        
        # Используем async context manager
        async with api_parser:
            articles = await api_parser.parse_crypto_data()
            
            print(f"📰 Получено {len(articles)} статей:")
            for i, article in enumerate(articles[:5], 1):  # Показываем первые 5
                print(f"   {i}. {article.title}")
                print(f"      Источник: {article.source}")
                print(f"      Категория: {article.category}")
                print(f"      Слов: {article.word_count}, Время чтения: {article.reading_time} мин")
                print()
                
    except Exception as e:
        print(f"❌ Ошибка при прямом тестировании: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("=" * 60)
    print("🤖 AiAlphaPulse - Парсер криптовалютных данных")
    print("=" * 60)
    
    # Запускаем тестирование
    asyncio.run(test_api_parser_directly())
    
    print("\n" + "=" * 60)
    print("🔄 Тестирование через ParsingService")
    print("=" * 60)
    
    asyncio.run(main())

