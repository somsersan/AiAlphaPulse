"""
Схема базы данных для нормализованных новостей
Поддержка PostgreSQL
"""
import psycopg2
from datetime import datetime
from typing import List, Dict


def create_normalized_articles_table(conn: psycopg2.extensions.connection):
    """Создание таблицы для нормализованных статей"""
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS normalized_articles (
        id SERIAL PRIMARY KEY,
        original_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        link TEXT,
        source TEXT,
        published_at TIMESTAMP,
        language_code TEXT,
        entities_json TEXT,  -- JSON строка со списком сущностей
        quality_score REAL,
        word_count INTEGER,
        is_processed BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    cursor = conn.cursor()
    cursor.execute(create_table_sql)
    
    # Создание индексов для оптимизации запросов
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_normalized_original_id ON normalized_articles(original_id);",
        "CREATE INDEX IF NOT EXISTS idx_normalized_published_at ON normalized_articles(published_at);",
        "CREATE INDEX IF NOT EXISTS idx_normalized_quality ON normalized_articles(quality_score);",
        "CREATE INDEX IF NOT EXISTS idx_normalized_language ON normalized_articles(language_code);",
        "CREATE INDEX IF NOT EXISTS idx_normalized_source ON normalized_articles(source);"
    ]
    
    for index_sql in indexes:
        cursor.execute(index_sql)
    
    conn.commit()


def create_processing_log_table(conn: psycopg2.extensions.connection):
    """Создание таблицы для логов обработки"""
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS processing_log (
        id SERIAL PRIMARY KEY,
        batch_id TEXT NOT NULL,
        total_articles INTEGER,
        processed_articles INTEGER,
        filtered_articles INTEGER,
        error_count INTEGER,
        processing_time_seconds REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    cursor = conn.cursor()
    cursor.execute(create_table_sql)
    conn.commit()


def get_processed_articles(conn: psycopg2.extensions.connection) -> set:
    """Получение списка уже обработанных статей"""
    cursor = conn.cursor()
    cursor.execute("SELECT original_id FROM normalized_articles")
    return {row[0] for row in cursor.fetchall()}


def get_max_processed_id(conn: psycopg2.extensions.connection) -> int:
    """Получение максимального ID уже обработанных статей"""
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(original_id) FROM normalized_articles")
    result = cursor.fetchone()[0]
    return result if result is not None else 0


def get_unprocessed_articles(conn: psycopg2.extensions.connection, limit: int = None) -> List[Dict]:
    """Получение необработанных статей (ID больше максимального обработанного)"""
    max_id = get_max_processed_id(conn)
    
    query = """
    SELECT id, title, link, source, published, is_processed, summary, content
    FROM financial_news_view
    WHERE id > %s
    ORDER BY id ASC
    """
    
    if limit:
        query += f" LIMIT {limit}"
    
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute(query, (max_id,))
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def insert_normalized_article(conn: psycopg2.extensions.connection, article: dict) -> int:
    """Вставка нормализованной статьи в базу"""
    
    insert_sql = """
    INSERT INTO normalized_articles 
    (original_id, title, content, link, source, published_at, language_code, 
     entities_json, quality_score, word_count, is_processed)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING id
    """
    
    import json
    
    cursor = conn.cursor()
    cursor.execute(insert_sql, (
        article['original_id'],
        article['title'],
        article['content'],
        article['link'],
        article['source'],
        article['published_at'],
        article['language_code'],
        json.dumps(article['entities'], ensure_ascii=False),
        article['quality_score'],
        article['word_count'],
        article['is_processed']
    ))
    
    conn.commit()
    return cursor.fetchone()[0]


def log_processing_batch(conn: psycopg2.extensions.connection, batch_info: dict):
    """Логирование информации о пакетной обработке"""
    
    insert_sql = """
    INSERT INTO processing_log 
    (batch_id, total_articles, processed_articles, filtered_articles, 
     error_count, processing_time_seconds)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    
    cursor = conn.cursor()
    cursor.execute(insert_sql, (
        batch_info['batch_id'],
        batch_info['total_articles'],
        batch_info['processed_articles'],
        batch_info['filtered_articles'],
        batch_info['error_count'],
        batch_info['processing_time_seconds']
    ))
    
    conn.commit()


def get_processing_stats(conn: psycopg2.extensions.connection) -> dict:
    """Получение статистики обработки"""
    
    stats = {}
    cursor = conn.cursor()
    
    # Общее количество статей в исходной таблице
    cursor.execute("SELECT COUNT(*) FROM financial_news_view")
    stats['total_original_articles'] = cursor.fetchone()[0]
    
    # Количество обработанных статей
    cursor.execute("SELECT COUNT(*) FROM normalized_articles")
    stats['total_processed_articles'] = cursor.fetchone()[0]
    
    # Статистика по языкам
    cursor.execute("""
        SELECT language_code, COUNT(*) 
        FROM normalized_articles 
        GROUP BY language_code 
        ORDER BY COUNT(*) DESC
    """)
    stats['language_distribution'] = dict(cursor.fetchall())
    
    # Средний балл качества
    cursor.execute("SELECT AVG(quality_score) FROM normalized_articles")
    avg_quality = cursor.fetchone()[0]
    stats['average_quality_score'] = round(avg_quality, 3) if avg_quality else 0
    
    # Статистика по источникам
    cursor.execute("""
        SELECT source, COUNT(*) 
        FROM normalized_articles 
        GROUP BY source 
        ORDER BY COUNT(*) DESC 
        LIMIT 10
    """)
    stats['top_sources'] = dict(cursor.fetchall())
    
    return stats
