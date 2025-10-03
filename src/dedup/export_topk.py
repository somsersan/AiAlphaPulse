import json, sqlite3, argparse
from datetime import datetime, timedelta

def export_topk(db, output, top_k=10, window_hours=48):
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row

    # выбираем кластеры по last_time в окне и сортируем по hotness
    q = """
    SELECT id, headline, lang, first_time, last_time,
           earliest_url, latest_url, strongest_domain,
           factors_json, hotness, urls_json, domains_json, doc_count
    FROM story_clusters
    WHERE last_time >= datetime('now', ?)
    ORDER BY hotness DESC
    LIMIT ?
    """
    rows = conn.execute(q, (f'-{window_hours} hours', top_k)).fetchall()

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
            k = """
            SELECT url FROM cluster_members
            WHERE cluster_id=? AND site=?
            ORDER BY time_utc DESC LIMIT 1
            """
            row = conn.execute(k, (cid, r["strongest_domain"])).fetchone()
            if row and row["url"]:
                links.append({"kind": "strongest", "url": row["url"]})

        # таймлайн
        timeline = {"first": r["first_time"], "update": r["last_time"], "confirm": None}
        # confirm — первая публикация с другого домена
        k2 = """
        SELECT site, time_utc
        FROM cluster_members
        WHERE cluster_id=?
        ORDER BY time_utc
        """
        sites_seen = set()
        for m in conn.execute(k2, (cid,)).fetchall():
            if sites_seen and m["site"] not in sites_seen and not timeline["confirm"]:
                timeline["confirm"] = m["time_utc"]
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
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "top_k": top_k,
            "window_hours": window_hours,
            "db": db
        },
        "clusters": clusters
    }

    with open(output, "w", encoding="utf-8") as f:
        json.dump(export, f, ensure_ascii=False, indent=2)

    conn.close()
    print(f"✅ экспортировано {len(clusters)} кластеров в {output}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/rss_articles.db")
    ap.add_argument("--out", default="radar_top.json")
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--window-hours", type=int, default=48)
    args = ap.parse_args()
    export_topk(args.db, args.out, args.top_k, args.window_hours)
