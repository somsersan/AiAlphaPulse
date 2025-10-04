"""Процессор для LLM анализа новостных кластеров"""
import json
import time
from typing import Dict, Optional
import psycopg2

from .openrouter_client import OpenRouterClient
from .schema import (
    create_llm_news_table,
    get_unprocessed_clusters,
    get_cluster_representative_article,
    insert_llm_analyzed_news
)


class LLMNewsProcessor:
    """Процессор для анализа новостей через LLM"""
    
    def __init__(self, conn: psycopg2.extensions.connection, api_key: str = None, 
                 model: str = None):
        self.conn = conn
        self.llm_client = OpenRouterClient(api_key=api_key, model=model)
        
        # Создаем таблицу если не существует
        create_llm_news_table(conn)
        
    def process_cluster(self, cluster_id: int) -> Optional[Dict]:
        """Обработать один кластер"""
        
        try:
            # СНАЧАЛА проверяем, не обработан ли уже этот кластер
            cursor = self.conn.cursor()
            cursor.execute("SELECT id FROM llm_analyzed_news WHERE id_cluster = %s", (cluster_id,))
            if cursor.fetchone():
                print(f"  ⏭️  Пропущен (обработан другим процессом)")
                return None
            
            # Получаем представительную статью из кластера
            article = get_cluster_representative_article(self.conn, cluster_id)
            
            if not article:
                print(f"⚠️  Кластер {cluster_id}: нет статей")
                return None
            
            print(f"📰 Обрабатываем кластер {cluster_id}: {article['title'][:60]}...")
            
            # Анализируем через LLM
            analysis = self.llm_client.analyze_news(
                headline=article['title'],
                content=article['content'] or article['title']
            )
            
            # Получаем все URL из кластера
            cursor = self.conn.cursor()
            try:
                cursor.execute("""
                    SELECT url FROM cluster_members 
                    WHERE cluster_id = %s AND url IS NOT NULL
                """, (cluster_id,))
                urls = [row[0] for row in cursor.fetchall()]
            except psycopg2.Error as e:
                self.conn.rollback()
                print(f"  ⚠️ Ошибка получения URL: {e}")
                urls = []
            
            # Подготавливаем данные для вставки
            data = {
                'id_old': article['normalized_id'],
                'id_cluster': cluster_id,
                'headline': article['title'],
                'content': article['content'],
                'urls_json': json.dumps(urls, ensure_ascii=False),
                'published_time': article['published_at'],
                'ai_hotness': analysis['hotness'],
                'tickers_json': json.dumps(analysis['tickers'], ensure_ascii=False),
                'reasoning': analysis.get('reasoning', '')  # Добавляем обоснование
            }
            
            # Вставляем в БД
            new_id = insert_llm_analyzed_news(self.conn, data)
            
            if not new_id:
                # Ошибка вставки - это не должно случаться, т.к. мы берем только необработанные
                print(f"  ❌ Не удалось вставить в БД (возможно дубликат)")
                return None
            
            reasoning_short = analysis.get('reasoning', '')[:80] + '...' if len(analysis.get('reasoning', '')) > 80 else analysis.get('reasoning', '')
            print(f"  ✅ ID={new_id} | 🔥 Hotness={analysis['hotness']:.3f} | 📊 Tickers={analysis['tickers']}")
            if reasoning_short:
                print(f"     💡 {reasoning_short}")
            return data
                
        except psycopg2.Error as e:
            # Откатываем транзакцию при любой ошибке БД
            self.conn.rollback()
            print(f"  ❌ Ошибка БД при обработке кластера {cluster_id}: {e}")
            return None
        except Exception as e:
            print(f"  ❌ Неожиданная ошибка при обработке кластера {cluster_id}: {e}")
            return None
    
    def process_batch(self, limit: int = 10, delay: float = 1.0) -> Dict:
        """Обработать пакет необработанных кластеров"""
        
        stats = {
            'processed': 0,
            'skipped': 0,
            'errors': 0
        }
        
        total_requested = limit
        batch_size = 50  # Запрашиваем небольшими порциями для свежести данных
        
        print(f"\n🔍 Начинаем обработку (цель: {total_requested} кластеров)...\n")
        
        while stats['processed'] < total_requested:
            # Сколько еще нужно обработать
            remaining = total_requested - stats['processed']
            fetch_limit = min(remaining, batch_size)
            
            # Получаем СВЕЖИЙ список необработанных кластеров
            clusters = get_unprocessed_clusters(self.conn, limit=fetch_limit)
            
            if not clusters:
                print(f"\n✅ Больше нет необработанных кластеров!")
                break
            
            print(f"📦 Батч: найдено {len(clusters)} необработанных кластеров")
            
            for cluster in clusters:
                # Текущий прогресс
                current = stats['processed'] + stats['skipped'] + stats['errors'] + 1
                
                try:
                    print(f"[{current}/{total_requested}] ", end="")
                    
                    result = self.process_cluster(cluster['cluster_id'])
                    
                    if result:
                        stats['processed'] += 1
                    elif result is None:
                        stats['skipped'] += 1
                    else:
                        stats['errors'] += 1
                    
                    # Задержка между запросами к API
                    time.sleep(delay)
                    
                    # Прерываем если достигли лимита ОБРАБОТАННЫХ (не считая пропущенные)
                    if stats['processed'] >= total_requested:
                        break
                        
                except Exception as e:
                    print(f"  ❌ Ошибка: {e}")
                    stats['errors'] += 1
                    continue
        
        print(f"\n{'='*60}")
        print(f"📊 ИТОГИ ОБРАБОТКИ")
        print(f"{'='*60}")
        print(f"✅ Обработано успешно: {stats['processed']}")
        print(f"⏭️  Пропущено (уже обработаны): {stats['skipped']}")
        print(f"❌ Ошибок: {stats['errors']}")
        total_attempts = stats['processed'] + stats['errors']
        if total_attempts > 0:
            print(f"📈 Успешность: {stats['processed']*100/total_attempts:.1f}%")
        
        return stats
    
    def get_top_hot_news(self, limit: int = 10, min_hotness: float = 0.7):
        """Получить топ самых горячих новостей"""
        
        query = """
        SELECT 
            id,
            headline,
            ai_hotness,
            tickers_json,
            published_time,
            urls_json
        FROM llm_analyzed_news
        WHERE ai_hotness >= %s
        ORDER BY ai_hotness DESC, published_time DESC
        LIMIT %s
        """
        
        cursor = self.conn.cursor()
        cursor.execute(query, (min_hotness, limit))
        
        columns = [desc[0] for desc in cursor.description]
        results = []
        for row in cursor.fetchall():
            data = dict(zip(columns, row))
            # Парсим JSON поля
            data['tickers'] = json.loads(data['tickers_json']) if data['tickers_json'] else []
            data['urls'] = json.loads(data['urls_json']) if data['urls_json'] else []
            results.append(data)
        
        return results

