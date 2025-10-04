import json, argparse
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Добавляем src в путь
sys.path.append(str(Path(__file__).parent.parent.parent))
from src.database import get_db_connection, get_db_cursor

def export_topk(output, top_k=10, window_hours=48):
    db_conn = get_db_connection()
    db_conn.connect()

    try:
        with get_db_cursor() as cursor:
            # выбираем кластеры по last_time в окне и сортируем по hotness
            q = """
            SELECT id, headline, lang, first_time, last_time,
                   earliest_url, latest_url, strongest_domain,
                   factors_json, hotness, urls_json, domains_json, doc_count
            FROM story_clusters
            WHERE last_time >= NOW() - INTERVAL '%s hours'
            ORDER BY hotness DESC
            LIMIT %s
            """
            cursor.execute(q, (window_hours, top_k))
            rows = cursor.fetchall()

        clusters = []
        for r in rows:
            cid = r["id"]
            # берём 3 ссылки для карточки (earliest/strongest/latest)
            links = []
            if r["earliest_url"]:
                links.append({"kind": "earliest", "url": r["earliest_url"]})
            if r["latest_url"]:
                links.append({"kind": "latest", "url": r["latest_url"]})
            if r["strongest_domain"]:
                # найдём любую ссылку с этим доменом
                with get_db_cursor() as cursor:
                    k = """
                    SELECT url FROM cluster_members
                    WHERE cluster_id=%s AND site=%s
                    ORDER BY time_utc DESC LIMIT 1
                    """
                    cursor.execute(k, (cid, r["strongest_domain"]))
                    row = cursor.fetchone()
                    if row and row["url"]:
                        links.append({"kind": "strongest", "url": row["url"]})

            # таймлайн
            timeline = {
                "first": r["first_time"].isoformat() if r["first_time"] else None, 
                "update": r["last_time"].isoformat() if r["last_time"] else None, 
                "confirm": None
            }
            # confirm — первая публикация с другого домена
            with get_db_cursor() as cursor:
                k2 = """
                SELECT site, time_utc
                FROM cluster_members
                WHERE cluster_id=%s
                ORDER BY time_utc
                """
                cursor.execute(k2, (cid,))
                sites_seen = set()
                for m in cursor.fetchall():
                    if sites_seen and m["site"] not in sites_seen and not timeline["confirm"]:
                        timeline["confirm"] = m["time_utc"].isoformat() if m["time_utc"] else None
                    sites_seen.add(m["site"])

            clusters.append({
                "dedup_group": cid,
                "headline": r["headline"],
                "hotness": round(r["hotness"] or 0.0, 3),
                "sources": links,
                "timeline": timeline,
                "domains": list((json.loads(r["domains_json"] or "{}")).keys()),
                "doc_count": r["doc_count"],
                "factors": json.loads(r["factors_json"] or "{}"),
            })

        export = {
            "meta": {
                "generated_at": datetime.now().isoformat(),
                "top_k": top_k,
                "window_hours": window_hours,
                "db": "PostgreSQL"
            },
            "clusters": clusters
        }

        with open(output, "w", encoding="utf-8") as f:
            json.dump(export, f, ensure_ascii=False, indent=2)

        print(f"✅ экспортировано {len(clusters)} кластеров в {output}")
        
    finally:
        db_conn.close()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="radar_top.json")
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--window-hours", type=int, default=48)
    args = ap.parse_args()
    export_topk(args.out, args.top_k, args.window_hours)
