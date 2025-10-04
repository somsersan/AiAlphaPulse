#!/usr/bin/env python3
"""
Скрипт для локальной инициализации базы данных PostgreSQL.
Использует настройки подключения из src.database
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from src.database import get_db_connection
from src.database.postgres_schema import create_all_tables


def main():
    """Инициализация базы данных"""
    print("🔄 Инициализация базы данных...")
    
    try:
        # Подключаемся
        db_conn = get_db_connection()
        db_conn.connect()
        
        print("✅ Подключение установлено")
        
        # Создаем все таблицы
        create_all_tables(db_conn._connection)
        
        print("✅ База данных инициализирована успешно!")
        
        db_conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка инициализации: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

