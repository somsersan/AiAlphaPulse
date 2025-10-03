"""CLI для запуска дедупликации новых нормализованных статей"""
import argparse
import sqlite3
from .schema import init
from .logic import process_new_batch


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="data/rss_articles.db", help="Путь к SQLite БД")
    args = p.parse_args()

    conn = sqlite3.connect(args.db)
    init(conn)

    try:
        n = process_new_batch(conn)
        print(f"\n✅ Готово. Добавлено/обновлено: {n} записей.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()