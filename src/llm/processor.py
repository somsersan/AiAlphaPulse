"""Processor for LLM analysis of news clusters"""
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
    """Processor for analyzing news via LLM"""
    
    def __init__(self, conn: psycopg2.extensions.connection, api_key: str = None, 
                 model: str = None):
        self.conn = conn
        self.llm_client = OpenRouterClient(api_key=api_key, model=model)
        
        # Create table if not exists
        create_llm_news_table(conn)
        
    def process_cluster(self, cluster_id: int) -> Optional[Dict]:
        """Process one cluster"""
        
        try:
            # FIRST check if cluster already processed
            cursor = self.conn.cursor()
            cursor.execute("SELECT id FROM llm_analyzed_news WHERE id_cluster = %s", (cluster_id,))
            if cursor.fetchone():
                print(f"  ⏭️  Skipped (processed by another process)")
                return None
            
            # Get representative article from cluster
            article = get_cluster_representative_article(self.conn, cluster_id)
            
            if not article:
                print(f"⚠️  Cluster {cluster_id}: no articles")
                return None
            
            print(f"📰 Processing cluster {cluster_id}: {article['title'][:60]}...")
            
            # Analyze via LLM
            analysis = self.llm_client.analyze_news(
                headline=article['title'],
                content=article['content'] or article['title']
            )
            
            # Get all URLs from cluster
            cursor = self.conn.cursor()
            try:
                cursor.execute("""
                    SELECT url FROM cluster_members 
                    WHERE cluster_id = %s AND url IS NOT NULL
                """, (cluster_id,))
                urls = [row[0] for row in cursor.fetchall()]
            except psycopg2.Error as e:
                self.conn.rollback()
                print(f"  ⚠️ Error getting URLs: {e}")
                urls = []
            
            # Prepare data for insertion
            data = {
                'id_old': article['normalized_id'],
                'id_cluster': cluster_id,
                'headline': article['title'],
                'content': article['content'],
                'urls_json': json.dumps(urls, ensure_ascii=False),
                'published_time': article['published_at'],
                'ai_hotness': analysis['hotness'],
                'tickers_json': json.dumps(analysis['tickers'], ensure_ascii=False),
                'reasoning': analysis.get('reasoning', '')  # Add reasoning
            }
            
            # Insert into DB
            new_id = insert_llm_analyzed_news(self.conn, data)
            
            if not new_id:
                # Insert error - should not happen since we only get unprocessed
                print(f"  ❌ Failed to insert into DB (possible duplicate)")
                return None
            
            reasoning_short = analysis.get('reasoning', '')[:80] + '...' if len(analysis.get('reasoning', '')) > 80 else analysis.get('reasoning', '')
            print(f"  ✅ ID={new_id} | 🔥 Hotness={analysis['hotness']:.3f} | 📊 Tickers={analysis['tickers']}")
            if reasoning_short:
                print(f"     💡 {reasoning_short}")
            return data
                
        except psycopg2.Error as e:
            # Rollback transaction on any DB error
            self.conn.rollback()
            print(f"  ❌ DB error processing cluster {cluster_id}: {e}")
            return None
        except Exception as e:
            print(f"  ❌ Unexpected error processing cluster {cluster_id}: {e}")
            return None
    
    def process_batch(self, limit: int = 10, delay: float = 1.0) -> Dict:
        """Process batch of unprocessed clusters"""
        
        stats = {
            'processed': 0,
            'skipped': 0,
            'errors': 0
        }
        
        total_requested = limit
        batch_size = 50  # Request in small batches for data freshness
        
        print(f"\n🔍 Starting processing (target: {total_requested} clusters)...\n")
        
        while stats['processed'] < total_requested:
            # How many more need to be processed
            remaining = total_requested - stats['processed']
            fetch_limit = min(remaining, batch_size)
            
            # Get FRESH list of unprocessed clusters
            clusters = get_unprocessed_clusters(self.conn, limit=fetch_limit)
            
            if not clusters:
                print(f"\n✅ No more unprocessed clusters!")
                break
            
            print(f"📦 Batch: found {len(clusters)} unprocessed clusters")
            
            for cluster in clusters:
                # Current progress
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
                    
                    # Delay between API requests
                    time.sleep(delay)
                    
                    # Break if reached limit of PROCESSED (not counting skipped)
                    if stats['processed'] >= total_requested:
                        break
                        
                except Exception as e:
                    print(f"  ❌ Error: {e}")
                    stats['errors'] += 1
                    continue
        
        print(f"\n{'='*60}")
        print(f"📊 PROCESSING SUMMARY")
        print(f"{'='*60}")
        print(f"✅ Processed successfully: {stats['processed']}")
        print(f"⏭️  Skipped (already processed): {stats['skipped']}")
        print(f"❌ Errors: {stats['errors']}")
        total_attempts = stats['processed'] + stats['errors']
        if total_attempts > 0:
            print(f"📈 Success rate: {stats['processed']*100/total_attempts:.1f}%")
        
        return stats
    
    def get_top_hot_news(self, limit: int = 10, min_hotness: float = 0.7):
        """Get top hottest news"""
        
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
            # Parse JSON fields
            data['tickers'] = json.loads(data['tickers_json']) if data['tickers_json'] else []
            data['urls'] = json.loads(data['urls_json']) if data['urls_json'] else []
            results.append(data)
        
        return results

