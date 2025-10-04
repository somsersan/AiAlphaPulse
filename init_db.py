#!/usr/bin/env python3
"""
Скрипт для инициализации базы данных PostgreSQL.
Запускается при первом запуске контейнера.
"""

import os
import sys
import time
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

def wait_for_db(database_url, max_retries=30):
    """Ждет, пока база данных станет доступной."""
    print("🔄 Ожидание подключения к базе данных...")
    
    for attempt in range(max_retries):
        try:
            engine = create_engine(database_url)
            with engine.connect() as conn:
                from sqlalchemy import text
                conn.execute(text("SELECT 1"))
            print("✅ База данных доступна!")
            return True
        except OperationalError as e:
            print(f"   Попытка {attempt + 1}/{max_retries}: {e}")
            time.sleep(2)
    
    print("❌ Не удалось подключиться к базе данных")
    return False

def init_database():
    """Инициализирует базу данных."""
    database_url = os.getenv('DATABASE_URL', 'postgresql://rss_user:rss_password@postgres:5432/rss_db')
    
    if not wait_for_db(database_url):
        sys.exit(1)
    
    try:
        from infrastructure.database.connection import db_connection
        from infrastructure.external.feed_initializer import FeedInitializer
        
        # Создаем таблицы
        db_connection.create_tables()
        print("✅ Таблицы созданы успешно")
        
        # Инициализируем ленты и каналы
        feed_initializer = FeedInitializer()
        import asyncio
        asyncio.run(feed_initializer.initialize_feeds())
        print("✅ Ленты и каналы инициализированы успешно")
        
    except Exception as e:
        print(f"❌ Ошибка инициализации базы данных: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_database()
