"""
Основной скрипт для обработки и нормализации новостных статей
"""
import json
import sqlite3
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from .normalizer import NewsNormalizer
from .database_schema import (
    create_normalized_articles_table,
    create_processing_log_table,
    get_processed_articles,
    get_max_processed_id,
    get_unprocessed_articles,
    insert_normalized_article,
    log_processing_batch,
    get_processing_stats
)


class ArticleProcessor:
    """Класс для обработки статей"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.normalizer = NewsNormalizer()
        self.conn = None
    
    def connect_db(self):
        """Подключение к базе данных"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
        # Создание таблиц
        create_normalized_articles_table(self.conn)
        create_processing_log_table(self.conn)
    
    def close_db(self):
        """Закрытие соединения с базой"""
        if self.conn:
            self.conn.close()
    
    def load_articles_from_json(self, json_path: str) -> List[Dict]:
        """Загрузка статей из JSON файла"""
        with open(json_path, 'r', encoding='utf-8') as f:
            articles = json.load(f)
        return articles
    
    def load_articles_from_db(self, limit: int = None) -> List[Dict]:
        """Загрузка статей из базы данных"""
        query = """
        SELECT id, title, link, source, published, is_processed, summary, content
        FROM articles
        ORDER BY published DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor = self.conn.execute(query)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def load_unprocessed_articles(self, limit: int = None) -> List[Dict]:
        """Загрузка только необработанных статей (эффективный метод)"""
        return get_unprocessed_articles(self.conn, limit)
    
    def get_processing_status(self) -> Dict:
        """Получение статуса обработки"""
        max_processed_id = get_max_processed_id(self.conn)
        processed_count = len(get_processed_articles(self.conn))
        
        # Получаем общее количество статей
        cursor = self.conn.execute("SELECT COUNT(*) FROM articles")
        total_articles = cursor.fetchone()[0]
        
        # Получаем максимальный ID в исходной таблице
        cursor = self.conn.execute("SELECT MAX(id) FROM articles")
        max_original_id = cursor.fetchone()[0] or 0
        
        return {
            'max_processed_id': max_processed_id,
            'processed_count': processed_count,
            'total_articles': total_articles,
            'max_original_id': max_original_id,
            'unprocessed_count': max_original_id - max_processed_id,
            'is_up_to_date': max_processed_id >= max_original_id
        }
    
    def process_articles_batch(self, articles: List[Dict], batch_size: int = 100) -> Dict:
        """Обработка пакета статей"""
        start_time = time.time()
        batch_id = str(uuid.uuid4())
        
        # Получаем уже обработанные статьи
        processed_ids = get_processed_articles(self.conn)
        
        stats = {
            'batch_id': batch_id,
            'total_articles': len(articles),
            'processed_articles': 0,
            'filtered_articles': 0,
            'error_count': 0,
            'processing_time_seconds': 0
        }
        
        print(f"Начинаем обработку пакета {batch_id}")
        print(f"Всего статей: {len(articles)}")
        print(f"Уже обработано: {len(processed_ids)}")
        
        for i, article in enumerate(articles):
            try:
                # Пропускаем уже обработанные статьи
                if article['id'] in processed_ids:
                    continue
                
                # Нормализация статьи
                normalized_article = self.normalizer.normalize_article(article)
                
                if normalized_article:
                    # Сохранение в базу
                    insert_normalized_article(self.conn, normalized_article)
                    stats['processed_articles'] += 1
                    
                    if stats['processed_articles'] % 10 == 0:
                        print(f"Обработано: {stats['processed_articles']}")
                else:
                    stats['filtered_articles'] += 1
                
            except Exception as e:
                print(f"Ошибка при обработке статьи {article.get('id', 'unknown')}: {e}")
                stats['error_count'] += 1
        
        # Завершение обработки
        end_time = time.time()
        stats['processing_time_seconds'] = round(end_time - start_time, 2)
        
        # Логирование результатов
        log_processing_batch(self.conn, stats)
        
        print(f"\nОбработка завершена за {stats['processing_time_seconds']} секунд")
        print(f"Обработано: {stats['processed_articles']}")
        print(f"Отфильтровано: {stats['filtered_articles']}")
        print(f"Ошибок: {stats['error_count']}")
        
        return stats
    
    def process_from_json(self, json_path: str, batch_size: int = 100):
        """Обработка статей из JSON файла"""
        print(f"Загружаем статьи из {json_path}")
        articles = self.load_articles_from_json(json_path)
        
        self.connect_db()
        try:
            self.process_articles_batch(articles, batch_size)
        finally:
            self.close_db()
    
    def process_from_db(self, limit: int = None, batch_size: int = 100):
        """Обработка статей из базы данных"""
        self.connect_db()
        try:
            print(f"Загружаем статьи из базы данных (лимит: {limit})")
            articles = self.load_articles_from_db(limit)
            self.process_articles_batch(articles, batch_size)
        finally:
            self.close_db()
    
    def process_unprocessed_articles(self, limit: int = None, batch_size: int = 100):
        """Обработка только необработанных статей (эффективный метод)"""
        self.connect_db()
        try:
            # Показываем статус
            status = self.get_processing_status()
            print(f"📊 Статус обработки:")
            print(f"   - Обработано статей: {status['processed_count']}")
            print(f"   - Всего статей: {status['total_articles']}")
            print(f"   - Необработано: {status['unprocessed_count']}")
            print(f"   - Максимальный обработанный ID: {status['max_processed_id']}")
            
            if status['is_up_to_date']:
                print("✅ Все статьи уже обработаны!")
                return
            
            print(f"🔄 Загружаем необработанные статьи (лимит: {limit})")
            articles = self.load_unprocessed_articles(limit)
            
            if not articles:
                print("ℹ️  Нет новых статей для обработки")
                return
            
            print(f"📝 Найдено {len(articles)} новых статей для обработки")
            self.process_articles_batch(articles, batch_size)
            
        finally:
            self.close_db()
    
    def show_processing_status(self):
        """Показать статус обработки"""
        self.connect_db()
        try:
            status = self.get_processing_status()
            
            print("=== СТАТУС ОБРАБОТКИ ===")
            print(f"Обработано статей: {status['processed_count']}")
            print(f"Всего статей: {status['total_articles']}")
            print(f"Необработано: {status['unprocessed_count']}")
            print(f"Максимальный обработанный ID: {status['max_processed_id']}")
            print(f"Максимальный исходный ID: {status['max_original_id']}")
            print(f"Актуальность: {'✅ Актуально' if status['is_up_to_date'] else '❌ Есть новые статьи'}")
            
        finally:
            self.close_db()
    
    def show_stats(self):
        """Показ статистики обработки"""
        self.connect_db()
        try:
            stats = get_processing_stats(self.conn)
            
            print("\n=== СТАТИСТИКА ОБРАБОТКИ ===")
            print(f"Всего статей в исходной таблице: {stats['total_original_articles']}")
            print(f"Обработано статей: {stats['total_processed_articles']}")
            print(f"Процент обработки: {(stats['total_processed_articles'] / stats['total_original_articles'] * 100):.1f}%")
            print(f"Средний балл качества: {stats['average_quality_score']}")
            
            print("\nРаспределение по языкам:")
            for lang, count in stats['language_distribution'].items():
                print(f"  {lang}: {count}")
            
            print("\nТоп источников:")
            for source, count in stats['top_sources'].items():
                print(f"  {source}: {count}")
                
        finally:
            self.close_db()


def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Обработка новостных статей')
    parser.add_argument('--json', help='Путь к JSON файлу с статьями')
    parser.add_argument('--db', help='Путь к базе данных', default='data/rss_articles.db')
    parser.add_argument('--limit', type=int, help='Лимит статей для обработки')
    parser.add_argument('--batch-size', type=int, default=100, help='Размер пакета')
    parser.add_argument('--stats', action='store_true', help='Показать статистику')
    parser.add_argument('--status', action='store_true', help='Показать статус обработки')
    parser.add_argument('--unprocessed', action='store_true', help='Обработать только необработанные статьи')
    
    args = parser.parse_args()
    
    processor = ArticleProcessor(args.db)
    
    if args.stats:
        processor.show_stats()
    elif args.status:
        processor.show_processing_status()
    elif args.json:
        processor.process_from_json(args.json, args.batch_size)
    elif args.unprocessed:
        processor.process_unprocessed_articles(args.limit, args.batch_size)
    else:
        processor.process_from_db(args.limit, args.batch_size)


if __name__ == "__main__":
    main()
