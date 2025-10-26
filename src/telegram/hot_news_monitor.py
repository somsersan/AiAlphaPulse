"""Hot news monitor for automatic notifications"""
import asyncio
import json
from datetime import datetime
from typing import Set
from telegram import Bot
from telegram.constants import ParseMode
from dotenv import load_dotenv
import os

from ..database import get_db_cursor
from .news_analyzer import NewsAnalyzer

load_dotenv()


class HotNewsMonitor:
    """Monitor and send notifications about hot news"""
    
    def __init__(self, hotness_threshold: float = 0.7, check_interval: int = 60):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set in .env")
        if not self.chat_id:
            raise ValueError("TELEGRAM_CHAT_ID not set in .env")
        
        self.bot = Bot(token=self.token)
        self.analyzer = NewsAnalyzer()
        
        self.hotness_threshold = hotness_threshold
        self.check_interval = check_interval
        self.notified_news: Set[int] = set()  # IDs of already sent news
    
    async def check_and_notify(self):
        """Check new hot news and send notifications"""
        
        # Get hot news that haven't been sent yet
        hot_news = self.get_hot_news()
        
        for news in hot_news:
            if news['id'] in self.notified_news:
                continue
            
            print(f"🔥 Sending hot news notification: {news['headline'][:50]}...")
            
            try:
                # Generate full analysis
                analysis = self.analyzer.generate_full_analysis({
                    'headline': news['headline'],
                    'content': news['content'],
                    'tickers': news['tickers'],
                    'hotness': news['ai_hotness'],
                    'urls': news.get('urls', []),
                    'published_at': news.get('published_time', ''),
                    'source': news.get('source', 'Unknown source')
                })
                
                # Format message
                message = self.format_hot_news_alert(news, analysis)
                
                # Send
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=message,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True
                )
                
                # Mark as sent
                self.notified_news.add(news['id'])
                
                print(f"✅ Notification sent")
                
                # Small delay between messages
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"❌ Notification send error: {e}")
    
    def get_hot_news(self):
        """Get unprocessed hot news"""
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    lan.id,
                    lan.headline,
                    lan.content,
                    lan.ai_hotness,
                    lan.tickers_json,
                    lan.urls_json,
                    lan.published_time,
                    sc.doc_count,
                    sc.first_time,
                    sc.last_time
                FROM llm_analyzed_news lan
                JOIN story_clusters sc ON lan.id_cluster = sc.id
                WHERE lan.ai_hotness >= %s
                ORDER BY lan.created_at DESC
                LIMIT 10
            """, (self.hotness_threshold,))
            
            news_list = []
            for row in cursor.fetchall():
                news_list.append({
                    'id': row['id'],
                    'headline': row['headline'],
                    'content': row['content'],
                    'ai_hotness': row['ai_hotness'],
                    'tickers': json.loads(row['tickers_json']) if row['tickers_json'] else [],
                    'urls': json.loads(row['urls_json']) if row['urls_json'] else [],
                    'published_time': row['published_time'],
                    'doc_count': row['doc_count'],
                    'first_time': row['first_time'],
                    'last_time': row['last_time']
                })
            
            return news_list
    
    def format_hot_news_alert(self, news: dict, analysis: dict) -> str:
        """Format hot news alert"""
        hotness = news['ai_hotness']
        
        # Get timeline for context
        first_time = news.get('first_time')
        last_time = news.get('last_time')
        timeline = f"First: {first_time.strftime('%d.%m %H:%M')}"
        if first_time and last_time and first_time != last_time:
            timeline += f" | Last: {last_time.strftime('%d.%m %H:%M')}"
        
        # Form alert header + ready analytical card
        header = f"""🚨 *HOT NEWS!*
🔥 *Hotness: {hotness:.2f}/1.00*
📄 *Documents in cluster:* {news.get('doc_count', 1)}
⏰ *Timeline:* {timeline}

{'='*40}
"""
        
        # Add ready analytical card
        analysis_card = analysis.get('analysis_text', 'Analysis unavailable')
        
        return header + analysis_card
    
    async def run(self):
        """Run monitoring in loop"""
        print(f"🔍 Hot news monitor started")
        print(f"   Hotness threshold: {self.hotness_threshold}")
        print(f"   Check interval: {self.check_interval}s")
        print(f"   Chat ID: {self.chat_id}")
        
        while True:
            try:
                await self.check_and_notify()
                await asyncio.sleep(self.check_interval)
            except KeyboardInterrupt:
                print("\n🛑 Stopping monitor...")
                break
            except Exception as e:
                print(f"❌ Monitor error: {e}")
                await asyncio.sleep(self.check_interval)




