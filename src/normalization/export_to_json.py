"""
Скрипт для экспорта нормализованных данных в JSON
"""
import json
import sqlite3
import argparse
from datetime import datetime
from pathlib import Path


def export_normalized_to_json(db_path: str, output_path: str, limit: int = None, min_quality: float = 0.0, language: str = None):
    """Экспорт нормализованных статей в JSON"""
    
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
    
    query += " ORDER BY quality_score DESC, published_at DESC"
    
    if limit:
        query += " LIMIT ?"
        params.append(limit)
    
    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    
    # Конвертация в список словарей
    articles = []
    for row in rows:
        article = dict(row)
        
        # Парсим JSON строку с сущностями
        try:
            article['entities'] = json.loads(article['entities_json'])
        except:
            article['entities'] = []
        
        # Удаляем исходное поле entities_json
        del article['entities_json']
        
        articles.append(article)
    
    # Создаем метаданные экспорта
    export_data = {
        'metadata': {
            'export_date': datetime.now().isoformat(),
            'total_articles': len(articles),
            'min_quality_filter': min_quality,
            'language_filter': language,
            'limit_applied': limit,
            'database_path': db_path
        },
        'articles': articles
    }
    
    # Сохранение в JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
    
    conn.close()
    
    print(f"✅ Экспортировано {len(articles)} статей в {output_path}")
    print(f"📊 Метаданные:")
    print(f"   - Дата экспорта: {export_data['metadata']['export_date']}")
    print(f"   - Минимальный балл качества: {min_quality}")
    print(f"   - Фильтр по языку: {language or 'не применен'}")
    print(f"   - Лимит: {limit or 'не применен'}")
    
    return len(articles)


def export_all_articles(db_path: str, output_path: str):
    """Экспорт всех нормализованных статей"""
    return export_normalized_to_json(db_path, output_path)


def export_high_quality_articles(db_path: str, output_path: str, min_quality: float = 0.8):
    """Экспорт только высококачественных статей"""
    return export_normalized_to_json(db_path, output_path, min_quality=min_quality)


def export_by_language(db_path: str, output_path: str, language: str, limit: int = None):
    """Экспорт статей по языку"""
    return export_normalized_to_json(db_path, output_path, language=language, limit=limit)


def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(description='Экспорт нормализованных статей в JSON')
    parser.add_argument('--db', default='data/rss_articles.db', help='Путь к базе данных')
    parser.add_argument('--output', default='normalized_articles.json', help='Путь к выходному файлу')
    parser.add_argument('--limit', type=int, help='Лимит статей для экспорта')
    parser.add_argument('--min-quality', type=float, default=0.0, help='Минимальный балл качества')
    parser.add_argument('--language', help='Фильтр по языку (ru, en, etc.)')
    parser.add_argument('--high-quality', action='store_true', help='Экспорт только высококачественных статей (>=0.8)')
    parser.add_argument('--all', action='store_true', help='Экспорт всех статей')
    
    args = parser.parse_args()
    
    # Определяем выходной файл
    if args.output == 'normalized_articles.json':
        if args.high_quality:
            args.output = 'high_quality_articles.json'
        elif args.language:
            args.output = f'articles_{args.language}.json'
        elif args.all:
            args.output = 'all_normalized_articles.json'
    
    # Устанавливаем параметры для высококачественных статей
    if args.high_quality:
        args.min_quality = 0.8
    
    try:
        count = export_normalized_to_json(
            args.db, 
            args.output, 
            args.limit, 
            args.min_quality, 
            args.language
        )
        print(f"\n🎉 Экспорт завершен успешно! Обработано {count} статей.")
        
    except Exception as e:
        print(f"❌ Ошибка при экспорте: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
