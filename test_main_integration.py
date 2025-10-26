"""
Тест интеграции APIParser с main_new.py
"""

import sys
import os

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Тестируем импорты."""
    print("🔧 Тестирование импортов...")
    
    try:
        from config.settings import settings
        print("✅ settings импортирован")
        
        from infrastructure.parsers.api_parser import APIParser
        print("✅ APIParser импортирован")
        
        from core.services.parsing_service import ParsingService
        print("✅ ParsingService импортирован")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка импорта: {e}")
        return False


def test_apiparser_creation():
    """Тестируем создание APIParser."""
    print("\n🔧 Тестирование создания APIParser...")
    
    try:
        from config.settings import settings
        from infrastructure.parsers.api_parser import APIParser
        
        # Создаем APIParser с настройками
        api_parser = APIParser(settings.crypto)
        print("✅ APIParser создан успешно")
        
        # Проверяем настройки
        print(f"📊 CoinGecko URL: {api_parser.crypto_settings.coingecko_api_url}")
        print(f"📊 Топ криптовалют: {len(api_parser.crypto_settings.top_cryptocurrencies)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка создания APIParser: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_parsing_service_integration():
    """Тестируем интеграцию с ParsingService."""
    print("\n🔧 Тестирование интеграции с ParsingService...")
    
    try:
        from config.settings import settings
        from infrastructure.parsers.api_parser import APIParser
        from core.services.parsing_service import ParsingService
        
        # Создаем APIParser
        api_parser = APIParser(settings.crypto)
        
        # Создаем мок-объекты для тестирования
        class MockRepository:
            pass
        
        # Создаем ParsingService с APIParser
        parsing_service = ParsingService(
            article_repository=MockRepository(),
            feed_repository=MockRepository(),
            rss_parser=None,
            telegram_parser=None,
            api_parser=api_parser
        )
        
        print("✅ ParsingService создан с APIParser")
        print(f"📊 API парсер установлен: {parsing_service.api_parser is not None}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка интеграции: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Основная функция тестирования."""
    print("=" * 60)
    print("🤖 Тестирование интеграции APIParser с main_new.py")
    print("=" * 60)
    
    # Тест 1: Импорты
    if not test_imports():
        print("❌ Тест импортов не пройден")
        return
    
    # Тест 2: Создание APIParser
    if not test_apiparser_creation():
        print("❌ Тест создания APIParser не пройден")
        return
    
    # Тест 3: Интеграция с ParsingService
    if not test_parsing_service_integration():
        print("❌ Тест интеграции не пройден")
        return
    
    print("\n" + "=" * 60)
    print("✅ Все тесты пройдены успешно!")
    print("🚀 APIParser готов к использованию в main_new.py")
    print("=" * 60)


if __name__ == "__main__":
    main()

