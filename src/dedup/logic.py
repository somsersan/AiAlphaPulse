from __future__ import annotations
import json
import psycopg2
from datetime import datetime, timezone, timedelta
from typing import Optional

import numpy as np

from .embedder import embed_text, MODEL_NAME  # импортируем MODEL_NAME
from .index_faiss import FaissIndex

# Пороги и параметры
TAU_DUP = 0.95
TAU_STORY = 0.89
WINDOW_HOURS = 48
K_NEIGHBORS = 30

SOURCE_WEIGHTS = {
    "sec.gov": 1.0,
    "reuters.com": 0.9,
    "bloomberg.com": 0.9,
    "ft.com": 0.85,
    "wsj.com": 0.85,
    "cnbc.com": 0.8,
}
DEFAULT_SOURCE_WEIGHT = 0.5


def _domain(site_or_url: str) -> str:
    from urllib.parse import urlparse
    host = site_or_url
    if "://" in site_or_url:
        host = urlparse(site_or_url).netloc
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def _source_weight(site_or_url: str) -> float:
    return SOURCE_WEIGHTS.get(_domain(site_or_url), DEFAULT_SOURCE_WEIGHT)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_aware_utc(dt) -> Optional[datetime]:
    """Привести datetime/строку к timezone-aware UTC (или None)."""
    if dt is None:
        return None
    if isinstance(dt, str):
        try:
            parsed = datetime.fromisoformat(dt)
        except Exception:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    # datetime
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# ---------- Загрузка/инициализация индекса ----------

def load_existing_vectors(conn: psycopg2.extensions.connection) -> tuple[Optional[FaissIndex], int]:
    cursor = conn.cursor()
    cursor.execute("SELECT normalized_id, embedding, dim FROM vectors ORDER BY normalized_id")
    rows = cursor.fetchall()
    if not rows:
        return None, 0
    dim = rows[0][2]
    index = FaissIndex(dim)
    vecs = []
    ids = []
    for nid, blob, d in rows:
        v = np.frombuffer(blob, dtype=np.float32)
        vecs.append(v)
        ids.append(nid)
    index.add_batch(np.vstack(vecs), ids)
    return index, ids[-1]


def fetch_new_normalized(conn: psycopg2.extensions.connection, last_id: int) -> list[dict]:
    q = """
      SELECT id, title, content, link, source, published_at, language_code
      FROM normalized_articles
      WHERE id > %s
      ORDER BY id ASC
    """
    cursor = conn.cursor()
    cursor.execute(q, (last_id,))
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in rows]


def get_cluster_of_doc(conn: psycopg2.extensions.connection, normalized_id: int) -> Optional[int]:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT cluster_id FROM cluster_members WHERE normalized_id=%s",
        (normalized_id,)
    )
    row = cursor.fetchone()
    return row[0] if row else None


# ---------- Решение о присвоении кластера ----------

def decide_cluster(
    conn: psycopg2.extensions.connection,
    neighbors: list[tuple[int, float]],
    lang: str,
    t_doc: datetime
) -> tuple[Optional[int], str]:
    # 1) Явный дубль
    for nid, sim in neighbors:
        if sim >= TAU_DUP:
            cid = get_cluster_of_doc(conn, nid)
            if cid:
                return cid, f"dup@{sim:.2f}"

    # 2) Тот же сюжет (порог по косинусу + окно времени и язык)
    window = timedelta(hours=WINDOW_HOURS)
    for nid, sim in neighbors:
        if TAU_STORY <= sim < TAU_DUP:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT language_code, published_at FROM normalized_articles WHERE id=%s",
                (nid,)
            )
            row = cursor.fetchone()
            if not row:
                continue
            if (row[0] or "") != (lang or ""):
                continue
            t_n = _to_aware_utc(row[1])
            if t_n is None:
                continue
            if abs((t_doc - t_n).total_seconds()) <= window.total_seconds():
                cid = get_cluster_of_doc(conn, nid)
                if cid:
                    return cid, f"story@{sim:.2f}"

    return None, "new"


# ---------- Операции с кластерами ----------

def ensure_cluster(
    conn: psycopg2.extensions.connection,
    headline: str,
    lang: str,
    url: str,
    site: str,
    t: datetime
) -> int:
    t = _to_aware_utc(t) or _now()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO story_clusters(
            headline, lang, first_time, last_time, domains_json, urls_json, doc_count
        )
        VALUES(%s,%s,%s,%s,%s,%s, 0)
        RETURNING id
        """,
        (
            headline,
            lang,
            t.isoformat(),
            t.isoformat(),
            json.dumps({site: 1}, ensure_ascii=False),
            json.dumps([url], ensure_ascii=False),
        ),
    )
    conn.commit()
    return cursor.fetchone()[0]


def add_member(
    conn: psycopg2.extensions.connection,
    cluster_id: int,
    normalized_id: int,
    url: str,
    site: str,
    t: datetime
):
    t = _to_aware_utc(t) or _now()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO cluster_members(cluster_id, normalized_id, url, site, time_utc) VALUES(%s,%s,%s,%s,%s) ON CONFLICT (cluster_id, normalized_id) DO UPDATE SET url=EXCLUDED.url, site=EXCLUDED.site, time_utc=EXCLUDED.time_utc",
        (cluster_id, normalized_id, url, site, t.isoformat()),
    )

    # обновить агрегаты кластера
    cursor.execute(
        "SELECT domains_json, urls_json, first_time, last_time FROM story_clusters WHERE id=%s",
        (cluster_id,),
    )
    row = cursor.fetchone()

    domains = json.loads(row[0] or "{}")
    urls = json.loads(row[1] or "[]")
    first_time = _to_aware_utc(row[2])
    last_time = _to_aware_utc(row[3])

    domains[site] = domains.get(site, 0) + 1
    if url and url not in urls:
        urls.append(url)
    if first_time is None or t < first_time:
        first_time = t
    if last_time is None or t > last_time:
        last_time = t

    cursor.execute(
        """
        UPDATE story_clusters
        SET domains_json=%s,
            urls_json=%s,
            first_time=%s,
            last_time=%s,
            doc_count=doc_count+1,
            updated_at=CURRENT_TIMESTAMP
        WHERE id=%s
        """,
        (
            json.dumps(domains, ensure_ascii=False),
            json.dumps(urls, ensure_ascii=False),
            first_time.isoformat(),
            last_time.isoformat(),
            cluster_id,
        ),
    )
    conn.commit()


def select_links_and_update(conn: psycopg2.extensions.connection, cluster_id: int):
    # earliest / strongest / latest
    cursor = conn.cursor()
    cursor.execute(
        "SELECT url, site, time_utc FROM cluster_members WHERE cluster_id=%s ORDER BY time_utc",
        (cluster_id,),
    )
    rows = cursor.fetchall()
    if not rows:
        return
    earliest = rows[0]
    latest = rows[-1]
    strongest = max(rows, key=lambda r: _source_weight(r[1]))
    cursor.execute(
        "UPDATE story_clusters SET earliest_url=%s, latest_url=%s, strongest_domain=%s WHERE id=%s",
        (earliest[0], latest[0], strongest[1], cluster_id),
    )
    conn.commit()


# ---------- Скоринг ----------

def _sigmoid(x: float) -> float:
    import math
    return 1.0 / (1.0 + math.exp(-x))


def recompute_scores(conn: psycopg2.extensions.connection, cluster_id: int):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT first_time, last_time, domains_json FROM story_clusters WHERE id=%s",
        (cluster_id,),
    )
    row = cursor.fetchone()
    if not row:
        return

    first, last, domains_json = row
    now = _now()
    first_dt = _to_aware_utc(first)
    age_h = (now - first_dt).total_seconds() / 3600.0 if first_dt else 9999.0
    novelty = 1.0 if age_h <= 6 else 0.3

    domains = json.loads(domains_json or "{}")
    src = 0.0
    for dom in domains.keys():
        src = max(src, _source_weight(dom))

    import math
    cnt = sum(domains.values())
    velocity = _sigmoid(math.log(cnt + 1))
    confirmation = min(len(domains) / 4.0, 1.0)
    materiality = 0.3  # плейсхолдер (можно читать из entities_json)
    breadth = 0.0      # плейсхолдер (если агрегируете entities)

    factors = {
        "novelty": float(novelty),
        "source": float(src),
        "velocity": float(velocity),
        "confirmation": float(confirmation),
        "materiality": float(materiality),
        "breadth": float(breadth),
    }
    hotness = (
        0.30 * factors["novelty"]
        + 0.20 * factors["source"]
        + 0.20 * factors["velocity"]
        + 0.15 * factors["confirmation"]
        + 0.10 * factors["materiality"]
        + 0.05 * factors["breadth"]
    )
    cursor.execute(
        "UPDATE story_clusters SET factors_json=%s, hotness=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s",
        (json.dumps(factors, ensure_ascii=False), hotness, cluster_id),
    )
    conn.commit()


# ---------- Основной цикл обработки ----------

def process_new_batch(conn: psycopg2.extensions.connection, k_neighbors: int = K_NEIGHBORS):
    # загрузить существующий индекс из БД (если есть)
    index, _ = load_existing_vectors(conn)

    # state
    cursor = conn.cursor()
    cursor.execute("SELECT last_vectorized_id FROM dedup_state WHERE id=1")
    row = cursor.fetchone()
    last_vec = row[0] if row else 0

    new_docs = fetch_new_normalized(conn, last_vec)
    if not new_docs:
        print("Нет новых нормализованных статей")
        return 0

    if index is None:
        # ленивая инициализация индекса при первом векторе
        dim = embed_text("x", "y").shape[0]
        index = FaissIndex(dim)

    processed = 0

    for d in new_docs:
        nid = int(d["id"])  # normalized_articles.id
        title = d["title"] or ""
        content = d["content"] or ""
        url = d["link"] or ""
        site = d["source"] or url
        lang = d["language_code"] or "unknown"

        t_doc = _to_aware_utc(d["published_at"]) or _now()

        v = embed_text(title, content)

        # записать вектор в БД и добавить в индекс
        cursor.execute(
            "INSERT INTO vectors(normalized_id, embedding, model, dim) VALUES(%s,%s,%s,%s) ON CONFLICT (normalized_id) DO UPDATE SET embedding=EXCLUDED.embedding, model=EXCLUDED.model, dim=EXCLUDED.dim",
            (nid, v.tobytes(), MODEL_NAME, v.shape[0]),
        )
        index.add_one(v, nid)

        # поиск соседей в индексе
        neighbors = index.search(v, k_neighbors)

        # решение о кластере
        cid, reason = decide_cluster(conn, neighbors, lang, t_doc)
        if cid is None:
            cid = ensure_cluster(
                conn,
                headline=title[:180],
                lang=lang,
                url=url,
                site=_domain(site),
                t=t_doc,
            )

        # добавить документ в кластер
        add_member(conn, cid, nid, url, _domain(site), t_doc)

        # обновить ссылки и скоринг
        select_links_and_update(conn, cid)
        recompute_scores(conn, cid)

        processed += 1

        # обновить state для инкрементальной обработки
        cursor.execute("UPDATE dedup_state SET last_vectorized_id=%s WHERE id=1", (nid,))
        conn.commit()

    print(f"Обработано новых нормализованных статей: {processed}")
    return processed
