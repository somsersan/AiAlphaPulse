"""CLI для запуска дедупликации новых нормализованных статей"""
import argparse
import sys
from pathlib import Path

# Добавляем src в путь
sys.path.append(str(Path(__file__).parent.parent.parent))
from src.database import get_db_connection
from .schema import init
from .logic import process_new_batch


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--k-neighbors", type=int, default=30, help="Количество соседей для поиска")
    args = p.parse_args()

    db_conn = get_db_connection()
    db_conn.connect()
    
    # Инициализируем таблицы дедупликации
    init(db_conn._connection)

    try:
        n = process_new_batch(db_conn._connection, args.k_neighbors)
        print(f"\n✅ Готово. Добавлено/обновлено: {n} записей.")
    finally:
        db_conn.close()

if __name__ == "__main__":
    main()