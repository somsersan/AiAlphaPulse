#!/usr/bin/env python3
"""
Скрипт для просмотра нормализованных данных
"""
import sqlite3
import json
import argparse
from datetime import datetime


def view_normalized_articles(db_path: str, limit: int = 10, min_quality: float = 0.0, language: str = None):
    """Просмотр нормализованных статей"""
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Формируем запрос
    query = """
    SELECT 
        original_id,
        title,
        content,
        link,
        source,
        published_at,
        language_code,
        entities_json,
        quality_score,
        word_count,
        created_at
    FROM normalized_articles
    WHERE quality_score >= ?
    """
    
    params = [min_quality]
    
    if language:
        query += " AND language_code = ?"
        params.append(language)
    
    query += " ORDER BY quality_score DESC, published_at DESC LIMIT ?"
    params.append(limit)
    
    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    
    print(f"=== НОРМАЛИЗОВАННЫЕ СТАТЬИ (показано {len(rows)} из {limit}) ===\n")
    
    for i, row in enumerate(rows, 1):
        print(f"--- СТАТЬЯ {i} ---")
        print(f"ID: {row['original_id']}")
        print(f"Заголовок: {row['title']}")
        print(f"Источник: {row['source']}")
        print(f"Язык: {row['language_code']}")
        print(f"Балл качества: {row['quality_score']:.2f}")
        print(f"Слов: {row['word_count']}")
        print(f"Опубликовано: {row['published_at']}")
        
        # Парсим сущности
        try:
            entities = json.loads(row['entities_json'])
            if entities:
                print(f"Сущности: {', '.join(entities[:10])}")  # Показываем первые 10
        except:
            print("Сущности: []")
        
        print(f"Ссылка: {row['link']}")
        
        # Показываем первые 200 символов контента
        content_preview = row['content'][:200]
        if len(row['content']) > 200:
            content_preview += "..."
        print(f"Контент: {content_preview}")
        
        print("-" * 80)
        print()
    
    conn.close()


def show_stats(db_path: str):
    """Показать статистику нормализованных данных"""
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    print("=== СТАТИСТИКА НОРМАЛИЗОВАННЫХ ДАННЫХ ===\n")
    
    # Общая статистика
    cursor = conn.execute("SELECT COUNT(*) FROM normalized_articles")
    total = cursor.fetchone()[0]
    print(f"Всего нормализованных статей: {total}")
    
    # Статистика по качеству
    cursor = conn.execute("""
        SELECT 
            MIN(quality_score) as min_quality,
            MAX(quality_score) as max_quality,
            AVG(quality_score) as avg_quality
        FROM normalized_articles
    """)
    quality_stats = cursor.fetchone()
    print(f"Балл качества: {quality_stats['min_quality']:.2f} - {quality_stats['max_quality']:.2f} (средний: {quality_stats['avg_quality']:.2f})")
    
    # Статистика по языкам
    print("\nРаспределение по языкам:")
    cursor = conn.execute("""
        SELECT language_code, COUNT(*) as count
        FROM normalized_articles 
        GROUP BY language_code 
        ORDER BY count DESC
    """)
    for row in cursor.fetchall():
        print(f"  {row['language_code']}: {row['count']}")
    
    # Статистика по источникам
    print("\nТоп-10 источников:")
    cursor = conn.execute("""
        SELECT source, COUNT(*) as count
        FROM normalized_articles 
        GROUP BY source 
        ORDER BY count DESC
        LIMIT 10
    """)
    for row in cursor.fetchall():
        print(f"  {row['source']}: {row['count']}")
    
    # Статистика по длине
    cursor = conn.execute("""
        SELECT 
            MIN(word_count) as min_words,
            MAX(word_count) as max_words,
            AVG(word_count) as avg_words
        FROM normalized_articles
    """)
    word_stats = cursor.fetchone()
    print(f"\nКоличество слов: {word_stats['min_words']} - {word_stats['max_words']} (среднее: {word_stats['avg_words']:.0f})")
    
    conn.close()


def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(description='Просмотр нормализованных данных')
    parser.add_argument('--db', default='data/rss_articles.db', help='Путь к базе данных')
    parser.add_argument('--limit', type=int, default=10, help='Количество статей для показа')
    parser.add_argument('--min-quality', type=float, default=0.0, help='Минимальный балл качества')
    parser.add_argument('--language', help='Фильтр по языку (ru, en, etc.)')
    parser.add_argument('--stats', action='store_true', help='Показать только статистику')
    
    args = parser.parse_args()
    
    if args.stats:
        show_stats(args.db)
    else:
        view_normalized_articles(args.db, args.limit, args.min_quality, args.language)


if __name__ == "__main__":
    main()
