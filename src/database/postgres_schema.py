"""
Схемы таблиц для PostgreSQL
Адаптированы из SQLite схем с сохранением всех полей и связей
"""
import psycopg2
from typing import List, Dict


def create_articles_table(conn: psycopg2.extensions.connection):
    """Создание таблицы articles (исходные статьи)"""
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS articles (
        id SERIAL PRIMARY KEY,
        title VARCHAR NOT NULL,
        link VARCHAR NOT NULL,
        published TIMESTAMP,
        summary TEXT,
        source VARCHAR,
        feed_url VARCHAR,
        content TEXT,
        author VARCHAR,
        category VARCHAR,
        image_url VARCHAR,
        word_count INTEGER,
        reading_time INTEGER,
        is_processed BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(title, link)
    );
    """
    
    conn.cursor().execute(create_table_sql)
    
    # Создание индексов
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published);",
        "CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source);",
        "CREATE INDEX IF NOT EXISTS idx_articles_created_at ON articles(created_at);",
        "CREATE INDEX IF NOT EXISTS idx_articles_is_processed ON articles(is_processed);"
    ]
    
    for index_sql in indexes:
        conn.cursor().execute(index_sql)
    
    conn.commit()


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
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (original_id) REFERENCES articles (id) ON DELETE CASCADE
    );
    """
    
    conn.cursor().execute(create_table_sql)
    
    # Создание индексов для оптимизации запросов
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_normalized_original_id ON normalized_articles(original_id);",
        "CREATE INDEX IF NOT EXISTS idx_normalized_published_at ON normalized_articles(published_at);",
        "CREATE INDEX IF NOT EXISTS idx_normalized_quality ON normalized_articles(quality_score);",
        "CREATE INDEX IF NOT EXISTS idx_normalized_language ON normalized_articles(language_code);",
        "CREATE INDEX IF NOT EXISTS idx_normalized_source ON normalized_articles(source);",
        "CREATE INDEX IF NOT EXISTS idx_normalized_created_at ON normalized_articles(created_at);"
    ]
    
    for index_sql in indexes:
        conn.cursor().execute(index_sql)
    
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
    
    conn.cursor().execute(create_table_sql)
    conn.commit()


def create_vectors_table(conn: psycopg2.extensions.connection):
    """Создание таблицы для векторов эмбеддингов"""
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS vectors (
        normalized_id INTEGER PRIMARY KEY,
        embedding BYTEA NOT NULL,       -- Бинарные данные эмбеддинга
        model TEXT NOT NULL,
        dim INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (normalized_id) REFERENCES normalized_articles(id) ON DELETE CASCADE
    );
    """
    
    conn.cursor().execute(create_table_sql)
    conn.commit()


def create_story_clusters_table(conn: psycopg2.extensions.connection):
    """Создание таблицы для кластеров новостных сюжетов"""
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS story_clusters (
        id SERIAL PRIMARY KEY,
        headline TEXT,
        lang TEXT,
        topic TEXT,
        first_time TIMESTAMP,
        last_time TIMESTAMP,
        domains_json TEXT,
        urls_json TEXT,
        doc_count INTEGER DEFAULT 0,
        strongest_domain TEXT,
        earliest_url TEXT,
        latest_url TEXT,
        factors_json TEXT,
        hotness REAL DEFAULT 0.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    conn.cursor().execute(create_table_sql)
    conn.commit()


def create_cluster_members_table(conn: psycopg2.extensions.connection):
    """Создание таблицы для связи кластеров и статей"""
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS cluster_members (
        cluster_id INTEGER NOT NULL,
        normalized_id INTEGER NOT NULL,
        url TEXT,
        site TEXT,
        time_utc TIMESTAMP,
        PRIMARY KEY (cluster_id, normalized_id),
        FOREIGN KEY (cluster_id) REFERENCES story_clusters(id) ON DELETE CASCADE,
        FOREIGN KEY (normalized_id) REFERENCES normalized_articles(id) ON DELETE CASCADE
    );
    """
    
    conn.cursor().execute(create_table_sql)
    
    # Создание индексов
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_members_cluster ON cluster_members(cluster_id);",
        "CREATE INDEX IF NOT EXISTS idx_members_time ON cluster_members(time_utc);"
    ]
    
    for index_sql in indexes:
        conn.cursor().execute(index_sql)
    
    conn.commit()


def create_dedup_state_table(conn: psycopg2.extensions.connection):
    """Создание таблицы для состояния дедупликации"""
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS dedup_state (
        id INTEGER PRIMARY KEY CHECK (id=1),
        last_vectorized_id INTEGER DEFAULT 0,
        last_clustered_id INTEGER DEFAULT 0
    );
    """
    
    conn.cursor().execute(create_table_sql)
    conn.commit()


def create_all_tables(conn: psycopg2.extensions.connection):
    """Создание всех таблиц в правильном порядке"""
    
    tables_creation_order = [
        create_articles_table,
        create_normalized_articles_table,
        create_processing_log_table,
        create_vectors_table,
        create_story_clusters_table,
        create_cluster_members_table,
        create_dedup_state_table
    ]
    
    print("🔄 Создание таблиц PostgreSQL...")
    
    for create_func in tables_creation_order:
        try:
            create_func(conn)
            print(f"✅ Таблица {create_func.__name__.replace('create_', '').replace('_table', '')} создана")
        except Exception as e:
            print(f"❌ Ошибка создания таблицы {create_func.__name__}: {e}")
            raise
    
    print("✅ Все таблицы созданы успешно!")


def get_table_info(conn: psycopg2.extensions.connection, table_name: str) -> Dict:
    """Получить информацию о таблице"""
    cursor = conn.cursor()
    
    # Получить информацию о колонках
    cursor.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns 
        WHERE table_name = %s
        ORDER BY ordinal_position
    """, (table_name,))
    
    columns = cursor.fetchall()
    
    # Получить информацию о внешних ключах
    cursor.execute("""
        SELECT 
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name = %s
    """, (table_name,))
    
    foreign_keys = cursor.fetchall()
    
    return {
        'columns': columns,
        'foreign_keys': foreign_keys
    }
