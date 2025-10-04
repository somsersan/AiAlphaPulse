"""Схема таблицы подписчиков на горячие новости"""
import psycopg2
from typing import List, Set


def create_subscribers_table(conn: psycopg2.extensions.connection):
    """Создание таблицы для подписчиков"""
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS telegram_subscribers (
        chat_id BIGINT PRIMARY KEY,
        username VARCHAR(255),
        first_name VARCHAR(255),
        last_name VARCHAR(255),
        subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN DEFAULT TRUE,
        last_notification_at TIMESTAMP
    );
    """
    
    cursor = conn.cursor()
    cursor.execute(create_table_sql)
    
    # Индекс для быстрого поиска активных подписчиков
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_subscribers_active 
        ON telegram_subscribers(is_active) 
        WHERE is_active = TRUE;
    """)
    
    conn.commit()
    print("✅ Таблица telegram_subscribers создана")


def add_subscriber(conn: psycopg2.extensions.connection, chat_id: int, 
                   username: str = None, first_name: str = None, last_name: str = None) -> bool:
    """Добавить подписчика"""
    
    insert_sql = """
    INSERT INTO telegram_subscribers (chat_id, username, first_name, last_name, is_active)
    VALUES (%s, %s, %s, %s, TRUE)
    ON CONFLICT (chat_id) 
    DO UPDATE SET 
        username = EXCLUDED.username,
        first_name = EXCLUDED.first_name,
        last_name = EXCLUDED.last_name,
        is_active = TRUE,
        subscribed_at = CURRENT_TIMESTAMP
    RETURNING chat_id
    """
    
    cursor = conn.cursor()
    cursor.execute(insert_sql, (chat_id, username, first_name, last_name))
    result = cursor.fetchone()
    conn.commit()
    
    return result is not None


def remove_subscriber(conn: psycopg2.extensions.connection, chat_id: int) -> bool:
    """Отписать пользователя (мягкое удаление)"""
    
    update_sql = """
    UPDATE telegram_subscribers 
    SET is_active = FALSE
    WHERE chat_id = %s
    RETURNING chat_id
    """
    
    cursor = conn.cursor()
    cursor.execute(update_sql, (chat_id,))
    result = cursor.fetchone()
    conn.commit()
    
    return result is not None


def get_active_subscribers(conn: psycopg2.extensions.connection) -> List[int]:
    """Получить список активных подписчиков"""
    
    query = """
    SELECT chat_id 
    FROM telegram_subscribers 
    WHERE is_active = TRUE
    ORDER BY subscribed_at
    """
    
    cursor = conn.cursor()
    cursor.execute(query)
    
    return [row[0] for row in cursor.fetchall()]


def get_active_subscribers_set(conn: psycopg2.extensions.connection) -> Set[int]:
    """Получить множество активных подписчиков для быстрой проверки"""
    return set(get_active_subscribers(conn))


def is_subscribed(conn: psycopg2.extensions.connection, chat_id: int) -> bool:
    """Проверить, подписан ли пользователь"""
    
    query = """
    SELECT 1 FROM telegram_subscribers 
    WHERE chat_id = %s AND is_active = TRUE
    """
    
    cursor = conn.cursor()
    cursor.execute(query, (chat_id,))
    
    return cursor.fetchone() is not None


def update_last_notification(conn: psycopg2.extensions.connection, chat_id: int):
    """Обновить время последнего уведомления"""
    
    update_sql = """
    UPDATE telegram_subscribers 
    SET last_notification_at = CURRENT_TIMESTAMP
    WHERE chat_id = %s
    """
    
    cursor = conn.cursor()
    cursor.execute(update_sql, (chat_id,))
    conn.commit()


def get_subscriber_stats(conn: psycopg2.extensions.connection) -> dict:
    """Получить статистику подписчиков"""
    
    query = """
    SELECT 
        COUNT(*) as total,
        COUNT(*) FILTER (WHERE is_active = TRUE) as active,
        COUNT(*) FILTER (WHERE is_active = FALSE) as inactive
    FROM telegram_subscribers
    """
    
    cursor = conn.cursor()
    cursor.execute(query)
    row = cursor.fetchone()
    
    return {
        'total': row[0] if row else 0,
        'active': row[1] if row else 0,
        'inactive': row[2] if row else 0
    }

