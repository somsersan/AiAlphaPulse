#!/usr/bin/env python3
"""
Тестирование подключения к PostgreSQL и просмотр данных
"""
import sys
from pathlib import Path

# Добавляем src в путь
sys.path.append(str(Path(__file__).parent / 'src'))
from database import get_db_connection, get_db_cursor


def test_postgres_connection():
    """Тестирование подключения к PostgreSQL"""
    print("🔌 Тестируем подключение к PostgreSQL...")
    
    try:
        db_conn = get_db_connection()
        db_conn.connect()
        
        with get_db_cursor() as cursor:
            # Получаем список таблиц
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = [row[0] for row in cursor.fetchall()]
            print("📋 Таблицы:", tables)
            
            # Подсчитываем записи в основных таблицах
            for table in ['articles', 'normalized_articles', 'story_clusters', 'cluster_members', 'vectors']:
                if table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    print(f"📊 {table}: {count} записей")
                else:
                    print(f"❌ Таблица {table} не найдена")
        
        print("✅ Подключение к PostgreSQL успешно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка подключения к PostgreSQL: {e}")
        return False
    finally:
        if 'db_conn' in locals():
            db_conn.close()


def show_sample_data():
    """Показать примеры данных"""
    print("\n📄 Примеры данных из основных таблиц:")
    
    try:
        db_conn = get_db_connection()
        db_conn.connect()
        
        with get_db_cursor() as cursor:
            # Примеры из articles
            cursor.execute("SELECT id, title, source, published FROM articles LIMIT 3")
            articles = cursor.fetchall()
            print("\n📰 Статьи (первые 3):")
            for article in articles:
                print(f"  ID: {article['id']}, Заголовок: {article['title'][:50]}..., Источник: {article['source']}")
            
            # Примеры из normalized_articles
            cursor.execute("SELECT original_id, title, quality_score, language_code FROM normalized_articles LIMIT 3")
            normalized = cursor.fetchall()
            print("\n📝 Нормализованные статьи (первые 3):")
            for norm in normalized:
                print(f"  ID: {norm['original_id']}, Заголовок: {norm['title'][:50]}..., Качество: {norm['quality_score']:.2f}, Язык: {norm['language_code']}")
            
            # Примеры из story_clusters
            cursor.execute("SELECT id, headline, doc_count, hotness FROM story_clusters LIMIT 3")
            clusters = cursor.fetchall()
            print("\n🔍 Кластеры новостей (первые 3):")
            for cluster in clusters:
                print(f"  ID: {cluster['id']}, Заголовок: {cluster['headline'][:50]}..., Документов: {cluster['doc_count']}, Горячность: {cluster['hotness']:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при получении данных: {e}")
        return False
    finally:
        if 'db_conn' in locals():
            db_conn.close()


def main():
    """Основная функция тестирования"""
    print("🧪 Тестирование PostgreSQL базы данных")
    print("=" * 50)
    
    if test_postgres_connection():
        show_sample_data()
    else:
        print("❌ Не удалось подключиться к базе данных")


if __name__ == "__main__":
    main()