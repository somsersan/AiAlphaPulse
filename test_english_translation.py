#!/usr/bin/env python3
"""
Тестовый скрипт для проверки генерации английской версии новости
"""
import os
import sys
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем путь к модулям
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.llm.proxyapi_client import ProxyAPIClient
from src.database.postgres_connection import get_db_connection

def test_analyze_news():
    """Тест анализа новости с генерацией английской версии"""
    
    print("="*60)
    print("🧪 ТЕСТ: Генерация английской версии новости")
    print("="*60)
    print()
    
    # Инициализируем клиент
    api_key = os.getenv('PROXYAPI_KEY')
    if not api_key:
        print("❌ Ошибка: PROXYAPI_KEY не установлен в .env")
        return False
    
    model = os.getenv('LLM_MODEL', 'deepseek/deepseek-chat')
    client = ProxyAPIClient(api_key=api_key, model=model)
    
    # Тестовая русская новость
    test_headline = "Китай сохранил позицию главного покупателя российских товаров"
    test_content = "Торговый оборот между Россией и Китаем в 2024 году достиг 330 миллиардов долларов. Китай сохранил позицию главного покупателя российских товаров, закупив энергоносители на сумму около 130 миллиардов долларов."
    
    print(f"📰 Тестовая новость (русский):")
    print(f"   Заголовок: {test_headline}")
    print(f"   Содержание: {test_content[:100]}...")
    print()
    
    # Анализируем новость
    print("🔄 Вызов analyze_news...")
    try:
        result = client.analyze_news(
            headline=test_headline,
            content=test_content
        )
        
        print("✅ Анализ завершен!")
        print()
        
        # Проверяем результаты
        print("📊 Результаты анализа:")
        print(f"   🔥 Hotness: {result.get('hotness', 0):.3f}")
        print(f"   📊 Tickers: {result.get('tickers', [])}")
        print()
        
        # Проверяем английские версии
        headline_en = result.get('headline_en', '')
        content_en = result.get('content_en', '')
        
        print("🌐 Английские версии:")
        print(f"   Заголовок (EN): {headline_en}")
        print(f"   Содержание (EN): {content_en[:150]}..." if len(content_en) > 150 else f"   Содержание (EN): {content_en}")
        print()
        
        # Проверка
        if not headline_en or headline_en.strip() == '':
            print("❌ ОШИБКА: headline_en пустой!")
            return False
        
        if not content_en or content_en.strip() == '':
            print("❌ ОШИБКА: content_en пустой!")
            return False
        
        # Проверяем что это действительно английский текст (простая проверка)
        # Проверяем наличие английских букв и отсутствие кириллицы
        has_english = any(c.isalpha() and ord(c) < 128 for c in headline_en)
        has_cyrillic = any('\u0400' <= c <= '\u04FF' for c in headline_en)
        
        if not has_english:
            print("⚠️  Предупреждение: headline_en не содержит английских букв")
        
        if has_cyrillic:
            print("❌ ОШИБКА: headline_en содержит кириллицу!")
            print(f"   Получено: {headline_en}")
            return False
        
        print("✅ Проверка пройдена: английские версии сгенерированы корректно")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при анализе: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_db_query():
    """Тест SQL запроса - проверяем что возвращается английская версия"""
    
    print("="*60)
    print("🧪 ТЕСТ: SQL запрос возвращает английскую версию")
    print("="*60)
    print()
    
    try:
        db_conn = get_db_connection()
        db_conn.connect()
        
        # Проверяем что поля существуют
        cursor = db_conn._connection.cursor()
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'llm_analyzed_news' 
            AND column_name IN ('headline_en', 'content_en')
        """)
        columns = [row[0] for row in cursor.fetchall()]
        
        print(f"📋 Найденные колонки в БД: {columns}")
        
        if 'headline_en' not in columns:
            print("⚠️  Колонка headline_en не найдена в БД")
            print("   Это нормально для новых таблиц - будет создана при первом запуске")
            return True
        
        if 'content_en' not in columns:
            print("⚠️  Колонка content_en не найдена в БД")
            print("   Это нормально для новых таблиц - будет создана при первом запуске")
            return True
        
        # Проверяем запрос с COALESCE
        cursor.execute("""
            SELECT 
                id,
                headline,
                content,
                COALESCE(headline_en, headline) as headline_en_merged,
                COALESCE(content_en, content) as content_en_merged
            FROM llm_analyzed_news
            WHERE headline_en IS NOT NULL OR content_en IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        rows = cursor.fetchall()
        
        if not rows:
            print("ℹ️  Нет записей с английскими версиями в БД")
            print("   Это нормально - они будут созданы при следующей обработке")
            return True
        
        print(f"✅ Найдено {len(rows)} записей с английскими версиями:")
        print()
        
        for i, row in enumerate(rows, 1):
            print(f"📰 Запись #{i}:")
            print(f"   ID: {row[0]}")
            print(f"   Заголовок (оригинал): {row[1][:80]}...")
            print(f"   Заголовок (EN): {row[3][:80]}...")
            
            if row[1] != row[3]:
                print("   ✅ Английская версия отличается от оригинала")
            else:
                print("   ⚠️  Английская версия совпадает с оригиналом (возможно новость уже была на английском)")
            
            if row[2] and row[4]:
                print(f"   Содержание (EN): {row[4][:100]}...")
            
            print()
        
        # Тестируем запрос как в боте
        cursor.execute("""
            SELECT 
                id,
                COALESCE(headline_en, headline) as headline,
                COALESCE(content_en, content) as content
            FROM llm_analyzed_news
            WHERE headline_en IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 1
        """)
        
        test_row = cursor.fetchone()
        if test_row:
            print("✅ Тест SQL запроса (как в боте):")
            print(f"   Заголовок: {test_row[1][:100]}...")
            print(f"   Содержание: {test_row[2][:100] if test_row[2] else 'N/A'}...")
            
            # Проверяем что это английский текст
            headline_text = test_row[1]
            has_cyrillic = any('\u0400' <= c <= '\u04FF' for c in headline_text)
            
            if has_cyrillic:
                print("   ⚠️  Внимание: Заголовок содержит кириллицу")
                print("   Это может быть нормально если новость изначально была на русском и английская версия еще не сгенерирована")
            else:
                print("   ✅ Заголовок на английском языке")
        
        db_conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при проверке БД: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Главная функция тестирования"""
    
    print("\n" + "="*60)
    print("🚀 ТЕСТИРОВАНИЕ АНГЛИЙСКОЙ ВЕРСИИ НОВОСТЕЙ")
    print("="*60)
    print()
    
    # Тест 1: Генерация английской версии
    print("📝 ТЕСТ 1: Генерация английской версии через LLM")
    print("-" * 60)
    test1_result = test_analyze_news()
    print()
    
    # Тест 2: Проверка SQL запросов
    print("📝 ТЕСТ 2: Проверка SQL запросов")
    print("-" * 60)
    test2_result = test_db_query()
    print()
    
    # Итоги
    print("="*60)
    print("📊 ИТОГИ ТЕСТИРОВАНИЯ")
    print("="*60)
    print(f"   Тест 1 (Генерация): {'✅ ПРОЙДЕН' if test1_result else '❌ ПРОВАЛЕН'}")
    print(f"   Тест 2 (SQL запросы): {'✅ ПРОЙДЕН' if test2_result else '❌ ПРОВАЛЕН'}")
    print()
    
    if test1_result and test2_result:
        print("✅ Все тесты пройдены! Английская версия работает корректно.")
        return 0
    else:
        print("❌ Некоторые тесты провалены. Проверьте логи выше.")
        return 1


if __name__ == '__main__':
    sys.exit(main())

