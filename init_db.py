#!/usr/bin/env python3
"""
Скрипт для инициализации базы данных PostgreSQL.
Запускается при первом запуске контейнера.
"""

import os
import sys
import time
import psycopg2
from psycopg2 import OperationalError

def wait_for_db(database_url, max_retries=30):
    """Ждет, пока база данных станет доступной."""
    print("🔄 Ожидание подключения к базе данных...")
    
    # Парсим URL для получения параметров подключения
    # Формат: postgresql://user:password@host:port/database
    parts = database_url.replace('postgresql://', '').split('@')
    user_pass = parts[0].split(':')
    host_db = parts[1].split('/')
    host_port = host_db[0].split(':')
    
    conn_params = {
        'user': user_pass[0],
        'password': user_pass[1],
        'host': host_port[0],
        'port': host_port[1] if len(host_port) > 1 else '5432',
        'database': host_db[1]
    }
    
    for attempt in range(max_retries):
        try:
            conn = psycopg2.connect(**conn_params)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            print("✅ База данных доступна!")
            return True, conn_params
        except OperationalError as e:
            print(f"   Попытка {attempt + 1}/{max_retries}: {e}")
            time.sleep(2)
    
    print("❌ Не удалось подключиться к базе данных")
    return False, None

def init_database():
    """Инициализирует базу данных."""
    database_url = os.getenv('DATABASE_URL', 'postgresql://rss_user:rss_password@postgres:5432/rss_db')
    
    success, conn_params = wait_for_db(database_url)
    if not success:
        sys.exit(1)
    
    try:
        # Импортируем схему и создаем таблицы
        from src.database.postgres_schema import create_all_tables
        
        conn = psycopg2.connect(**conn_params)
        create_all_tables(conn)
        conn.close()
        
        print("✅ База данных инициализирована успешно")
        
    except Exception as e:
        print(f"❌ Ошибка инициализации базы данных: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    init_database()
