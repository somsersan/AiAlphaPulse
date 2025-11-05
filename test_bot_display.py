#!/usr/bin/env python3
"""
Финальный тест - демонстрация как новость будет выглядеть в боте
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.llm.proxyapi_client import ProxyAPIClient
from src.telegram.bot import NewsBot

def test_bot_display():
    """Тест отображения новости в боте"""
    
    print("="*60)
    print("🧪 ТЕСТ: Отображение новости в боте")
    print("="*60)
    print()
    
    # Инициализируем клиент
    api_key = os.getenv('PROXYAPI_KEY')
    model = os.getenv('LLM_MODEL', 'deepseek/deepseek-chat')
    client = ProxyAPIClient(api_key=api_key, model=model)
    
    # Тестовая русская новость (как в примере)
    test_headline = "Китай сохранил позицию главного покупателя российских товаров"
    test_content = "Торговый оборот между Россией и Китаем в 2024 году достиг 330 миллиардов долларов. Китай сохранил позицию главного покупателя российских товаров, закупив энергоносители на сумму около 130 миллиардов долларов."
    
    print("📰 Исходная новость (русский):")
    print(f"   Заголовок: {test_headline}")
    print(f"   Содержание: {test_content}")
    print()
    
    # Анализируем
    print("🔄 Анализ новости...")
    result = client.analyze_news(headline=test_headline, content=test_content)
    
    # Создаем объект новости как в БД
    from datetime import datetime
    news_dict = {
        'id': 9999,
        'headline': result['headline_en'],  # Используем английскую версию
        'content': result['content_en'],     # Используем английскую версию
        'ai_hotness': result['hotness'],
        'tickers': result['tickers'],
        'urls': ['https://example.com/news/1'],
        'published_time': datetime.now(),
        'first_time': datetime.now(),
        'last_time': datetime.now(),
        'doc_count': 1
    }
    
    print("✅ Анализ завершен")
    print()
    
    # Форматируем как в боте
    bot = NewsBot()
    formatted_message = bot.format_news_message(news_dict, index=1, total=1)
    
    print("="*60)
    print("📱 КАК НОВОСТЬ БУДЕТ ВЫГЛЯДЕТЬ В БОТЕ:")
    print("="*60)
    print()
    print(formatted_message)
    print()
    print("="*60)
    print()
    
    # Проверяем что текст на английском
    if 'China' in formatted_message or 'Maintains' in formatted_message or 'Position' in formatted_message:
        print("✅ УСПЕХ: В сообщении используется английский текст!")
        print(f"   Заголовок на английском: {result['headline_en']}")
        return True
    else:
        print("❌ ОШИБКА: В сообщении не найден английский текст")
        return False


if __name__ == '__main__':
    test_bot_display()

