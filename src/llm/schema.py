"""Схема таблицы для результатов LLM анализа"""
import psycopg2


def create_llm_news_table(conn: psycopg2.extensions.connection):
    """Создание таблицы для результатов LLM анализа новостей"""
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS llm_analyzed_news (
        id SERIAL PRIMARY KEY,
        id_old INTEGER NOT NULL,  -- ID из normalized_articles
        id_cluster INTEGER NOT NULL,  -- ID из story_clusters
        headline TEXT NOT NULL,
        content TEXT,
        urls_json TEXT,  -- JSON массив ссылок
        published_time TIMESTAMP,
        ai_hotness REAL,  -- Оценка горячности от LLM (0-1)
        tickers_json TEXT,  -- JSON массив тикеров
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(id_cluster),  -- Один кластер обрабатывается только раз
        FOREIGN KEY (id_old) REFERENCES normalized_articles(id) ON DELETE CASCADE,
        FOREIGN KEY (id_cluster) REFERENCES story_clusters(id) ON DELETE CASCADE
    );
    """
    
    cursor = conn.cursor()
    cursor.execute(create_table_sql)
    
    # Индексы для быстрого поиска
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_llm_news_cluster ON llm_analyzed_news(id_cluster);",
        "CREATE INDEX IF NOT EXISTS idx_llm_news_hotness ON llm_analyzed_news(ai_hotness DESC);",
        "CREATE INDEX IF NOT EXISTS idx_llm_news_published ON llm_analyzed_news(published_time DESC);"
    ]
    
    for index_sql in indexes:
        cursor.execute(index_sql)
    
    conn.commit()
    print("✅ Таблица llm_analyzed_news создана")


def get_unprocessed_clusters(conn: psycopg2.extensions.connection, limit: int = None):
    """Получить необработанные кластеры"""
    
    query = """
    SELECT 
        sc.id as cluster_id,
        sc.headline,
        sc.first_time,
        sc.doc_count,
        sc.urls_json,
        sc.hotness as original_hotness
    FROM story_clusters sc
    LEFT JOIN llm_analyzed_news lan ON sc.id = lan.id_cluster
    WHERE lan.id IS NULL  -- Еще не обработаны
    ORDER BY sc.first_time DESC
    """
    
    if limit:
        query += f" LIMIT {limit}"
    
    cursor = conn.cursor()
    cursor.execute(query)
    
    columns = [desc[0] for desc in cursor.description]
    results = []
    for row in cursor.fetchall():
        results.append(dict(zip(columns, row)))
    
    return results


def get_cluster_representative_article(conn: psycopg2.extensions.connection, cluster_id: int):
    """Получить представительную статью из кластера"""
    
    query = """
    SELECT 
        na.id as normalized_id,
        na.title,
        na.content,
        na.published_at,
        cm.url
    FROM cluster_members cm
    JOIN normalized_articles na ON cm.normalized_id = na.id
    WHERE cm.cluster_id = %s
    ORDER BY cm.time_utc ASC  -- Берем самую раннюю
    LIMIT 1
    """
    
    cursor = conn.cursor()
    cursor.execute(query, (cluster_id,))
    
    row = cursor.fetchone()
    if not row:
        return None
    
    columns = [desc[0] for desc in cursor.description]
    return dict(zip(columns, row))


def insert_llm_analyzed_news(conn: psycopg2.extensions.connection, data: dict):
    """Вставить результат LLM анализа"""
    
    insert_sql = """
    INSERT INTO llm_analyzed_news 
        (id_old, id_cluster, headline, content, urls_json, published_time, 
         ai_hotness, tickers_json)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (id_cluster) DO NOTHING
    RETURNING id
    """
    
    cursor = conn.cursor()
    cursor.execute(insert_sql, (
        data['id_old'],
        data['id_cluster'],
        data['headline'],
        data['content'],
        data['urls_json'],
        data['published_time'],
        data['ai_hotness'],
        data['tickers_json']
    ))
    
    result = cursor.fetchone()
    conn.commit()
    
    return result[0] if result else None

