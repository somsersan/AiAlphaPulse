"""Схема таблиц для дедупа поверх normalized_articles"""
from __future__ import annotations
import sqlite3

DDL = {
    "vectors": """
    CREATE TABLE IF NOT EXISTS vectors (
      normalized_id INTEGER PRIMARY KEY,
      embedding BLOB NOT NULL,       -- np.float32.tobytes()
      model TEXT NOT NULL,
      dim INTEGER NOT NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (normalized_id) REFERENCES normalized_articles(id)
    );
    """,
    "story_clusters": """
    CREATE TABLE IF NOT EXISTS story_clusters (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      headline TEXT,
      lang TEXT,
      topic TEXT,
      first_time DATETIME,
      last_time DATETIME,
      domains_json TEXT,
      urls_json TEXT,
      doc_count INTEGER DEFAULT 0,
      strongest_domain TEXT,
      earliest_url TEXT,
      latest_url TEXT,
      factors_json TEXT,
      hotness REAL DEFAULT 0.0,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """,
    "cluster_members": """
    CREATE TABLE IF NOT EXISTS cluster_members (
      cluster_id INTEGER NOT NULL,
      normalized_id INTEGER NOT NULL,
      url TEXT,
      site TEXT,
      time_utc DATETIME,
      PRIMARY KEY (cluster_id, normalized_id),
      FOREIGN KEY (cluster_id) REFERENCES story_clusters(id),
      FOREIGN KEY (normalized_id) REFERENCES normalized_articles(id)
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


def init(conn: sqlite3.Connection):
    for k, sql in DDL.items():
        conn.executescript(sql)
    # ensure state row exists
    cur = conn.execute("SELECT COUNT(*) FROM dedup_state WHERE id=1")
    if cur.fetchone()[0] == 0:
        conn.execute("INSERT INTO dedup_state(id,last_vectorized_id,last_clustered_id) VALUES(1,0,0)")
    conn.commit()