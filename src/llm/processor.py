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
        cursor.execute("""
            SELECT url FROM cluster_members 
            WHERE cluster_id = %s AND url IS NOT NULL
        """, (cluster_id,))
        urls = [row[0] for row in cursor.fetchall()]
        
        # Подготавливаем данные для вставки
        data = {
            'id_old': article['normalized_id'],
            'id_cluster': cluster_id,
            'headline': article['title'],
            'content': article['content'],
            'urls_json': json.dumps(urls, ensure_ascii=False),
            'published_time': article['published_at'],
            'ai_hotness': analysis['hotness'],
            'tickers_json': json.dumps(analysis['tickers'], ensure_ascii=False)
        }
        
        # Вставляем в БД
        new_id = insert_llm_analyzed_news(self.conn, data)
        
        if new_id:
            print(f"  ✅ ID={new_id} | 🔥 Hotness={analysis['hotness']:.3f} | 📊 Tickers={analysis['tickers']}")
            return data
        else:
            print(f"  ⚠️  Кластер уже обработан")
            return None
    
    def process_batch(self, limit: int = 10, delay: float = 1.0) -> Dict:
        """Обработать пакет необработанных кластеров"""
        
        print(f"\n🔍 Ищем необработанные кластеры (лимит: {limit})...")
        
        clusters = get_unprocessed_clusters(self.conn, limit=limit)
        
        if not clusters:
            print("✅ Все кластеры уже обработаны")
            return {
                'processed': 0,
                'skipped': 0,
                'errors': 0
            }
        
        print(f"📊 Найдено необработанных кластеров: {len(clusters)}\n")
        
        stats = {
            'processed': 0,
            'skipped': 0,
            'errors': 0
        }
        
        for i, cluster in enumerate(clusters, 1):
            try:
                print(f"[{i}/{len(clusters)}] ", end="")
                
                result = self.process_cluster(cluster['cluster_id'])
                
                if result:
                    stats['processed'] += 1
                else:
                    stats['skipped'] += 1
                
                # Задержка между запросами к API
                if i < len(clusters):
                    time.sleep(delay)
                    
            except Exception as e:
                print(f"  ❌ Ошибка: {e}")
                stats['errors'] += 1
                continue
        
        print(f"\n{'='*60}")
        print(f"📊 ИТОГИ ОБРАБОТКИ")
        print(f"{'='*60}")
        print(f"✅ Обработано: {stats['processed']}")
        print(f"⏭️  Пропущено: {stats['skipped']}")
        print(f"❌ Ошибок: {stats['errors']}")
        
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

