"""Схема таблиц для дедупа поверх normalized_articles - PostgreSQL версия"""
from __future__ import annotations
import psycopg2

DDL = {
    "vectors": """
    CREATE TABLE IF NOT EXISTS vectors (
      normalized_id INTEGER PRIMARY KEY,
      embedding BYTEA NOT NULL,       -- Бинарные данные эмбеддинга
      model TEXT NOT NULL,
      dim INTEGER NOT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (normalized_id) REFERENCES normalized_articles(id) ON DELETE CASCADE
    );
    """,
    "story_clusters": """
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
    """,
    "cluster_members": """
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
    """,
    "state": """
    CREATE TABLE IF NOT EXISTS dedup_state (
      id INTEGER PRIMARY KEY CHECK (id=1),
      last_vectorized_id INTEGER DEFAULT 0,
      last_clustered_id INTEGER DEFAULT 0
    );
    """,
    "idx": """
    CREATE INDEX IF NOT EXISTS idx_members_cluster ON cluster_members(cluster_id);
    CREATE INDEX IF NOT EXISTS idx_members_time ON cluster_members(time_utc);
    CREATE INDEX IF NOT EXISTS idx_norm_published ON normalized_articles(published_at);
    """,
}


def init(conn: psycopg2.extensions.connection):
    cursor = conn.cursor()
    for k, sql in DDL.items():
        cursor.execute(sql)
    # ensure state row exists
    cursor.execute("SELECT COUNT(*) FROM dedup_state WHERE id=1")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO dedup_state(id,last_vectorized_id,last_clustered_id) VALUES(1,0,0)")
    conn.commit()