"""Telegram bot for sending news"""
import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Set
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode
from html import escape
from dotenv import load_dotenv

from ..database import get_db_cursor, get_db_connection
from .news_analyzer import NewsAnalyzer
from .subscribers_schema import (
    create_subscribers_table,
    add_subscriber,
    remove_subscriber,
    get_active_subscribers,
    is_subscribed,
    update_last_notification,
    get_subscriber_stats
)

load_dotenv()


class NewsBot:
    """Telegram bot for news"""
    
    def __init__(self, enable_monitor: bool = True, hotness_threshold: float = 0.7, check_interval: int = 60):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set in .env")
        
        # TELEGRAM_CHAT_ID is now optional - using subscribers from DB
        self.legacy_chat_id = os.getenv('TELEGRAM_CHAT_ID')  # For backward compatibility
        
        self.analyzer = NewsAnalyzer()
        self.app = Application.builder().token(self.token).build()
        
        # Configure timeouts to avoid connection errors
        self.app.bot.request.timeout = 30
        self.app.bot.request.connect_timeout = 10
        
        # Register commands
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("top", self.top_command))
        self.app.add_handler(CommandHandler("latest", self.latest_command))
        self.app.add_handler(CommandHandler("search", self.search_command))
        self.app.add_handler(CommandHandler("subscribe", self.subscribe_command))
        self.app.add_handler(CommandHandler("unsubscribe", self.unsubscribe_command))
        self.app.add_handler(CommandHandler("mystatus", self.mystatus_command))
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Initialize subscribers table
        self._init_subscribers_table()
        
        # Hot news monitor settings
        self.enable_monitor = enable_monitor
        self.hotness_threshold = hotness_threshold
        self.check_interval = check_interval
        self.notified_news: Set[int] = set()
    
    def _init_subscribers_table(self):
        """Initialize subscribers table"""
        try:
            db_conn = get_db_connection()
            db_conn.connect()
            create_subscribers_table(db_conn._connection)
            
            # If legacy TELEGRAM_CHAT_ID exists, add it as subscriber
            if self.legacy_chat_id:
                try:
                    chat_id = int(self.legacy_chat_id)
                    add_subscriber(db_conn._connection, chat_id, username="legacy_user")
                    print(f"✅ Legacy chat_id {chat_id} added to subscribers")
                except:
                    pass
            
            db_conn.close()
        except Exception as e:
            print(f"⚠️ Error initializing subscribers table: {e}")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Command /start"""
        welcome_message = """
🔥 <b>Welcome to AI Alpha Pulse!</b>

I'll help you track the hottest financial news.

📊 <b>Available commands:</b>
/top - Top news by hotness
/latest - Latest added news
/search - Search news by keywords
/subscribe - Subscribe to notifications
/unsubscribe - Unsubscribe from notifications
/mystatus - Check subscription status
/help - Help

📌 <b>Examples:</b>
<code>/top 10 24</code> - Top 10 for 24 hours
<code>/top 5 48</code> - Top 5 for 48 hours
<code>/latest 5</code> - Latest 5 news
<code>/latest</code> - Latest 10 news
<code>/search Bitcoin</code> - Search for Bitcoin
<code>/search BTC ETH</code> - Search for BTC or ETH

🔔 <b>Auto-notifications:</b>
Subscribe with /subscribe to receive hot news (hotness ≥ 0.7) automatically!
        """
        await update.message.reply_text(welcome_message, parse_mode=ParseMode.HTML)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Command /help"""
        help_text = """
📖 <b>Command Help</b>

<b>1️⃣ Top by hotness:</b>
<code>/top [count] [hours]</code>
• count - how many news items (1-20, default: 10)
• hours - time period (1-168, default: 24)

<b>Examples:</b>
<code>/top</code> - Top 10 for last 24 hours
<code>/top 5</code> - Top 5 for last 24 hours  
<code>/top 15 48</code> - Top 15 for last 48 hours

<b>2️⃣ Latest news:</b>
<code>/latest [count]</code>
• count - how many news items (1-20, default: 10)

<b>Examples:</b>
<code>/latest</code> - Latest 10 news
<code>/latest 5</code> - Latest 5 news
<code>/latest 20</code> - Latest 20 news

<b>3️⃣ Search news:</b>
<code>/search keyword1 [keyword2 ...]</code>
• Search by one or multiple keywords
• Searches in headline and content
• Returns up to 10 most recent matches

<b>Examples:</b>
<code>/search Bitcoin</code> - Find news about Bitcoin
<code>/search BTC ETH</code> - Find news with BTC or ETH
<code>/search bull market</code> - Find news about bull market

📊 <b>What's shown:</b>
• News headline
• Hotness score (0-1)
• Tickers/assets
• Source links
• Publication time
• Button for detailed analysis

🔥 <b>For hot news</b> (≥0.7):
• Trading signal
• Asset recommendations
        """
        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)
    
    async def subscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Command /subscribe - subscribe to notifications"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        try:
            db_conn = get_db_connection()
            db_conn.connect()
            
            # Check if already subscribed
            if is_subscribed(db_conn._connection, chat_id):
                await update.message.reply_text(
                    "✅ You are already subscribed to hot news notifications!"
                )
                db_conn.close()
                return
            
            # Add subscriber
            success = add_subscriber(
                db_conn._connection,
                chat_id=chat_id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            
            db_conn.close()
            
            if success:
                await update.message.reply_text(
                    "🔔 <b>Subscription activated!</b>\n\n"
                    "You will now receive notifications about hot news (hotness ≥ 0.7).\n\n"
                    "To unsubscribe use /unsubscribe",
                    parse_mode=ParseMode.HTML
                )
            else:
                await update.message.reply_text(
                    "❌ Subscription error. Please try later."
                )
                
        except Exception as e:
            print(f"❌ Subscription error: {e}")
            await update.message.reply_text(
                "❌ An error occurred. Please try later."
            )
    
    async def unsubscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Command /unsubscribe - unsubscribe from notifications"""
        chat_id = update.effective_chat.id
        
        try:
            db_conn = get_db_connection()
            db_conn.connect()
            
            # Check if subscribed
            if not is_subscribed(db_conn._connection, chat_id):
                await update.message.reply_text(
                    "ℹ️ You are not subscribed to notifications.\n\n"
                    "To subscribe use /subscribe"
                )
                db_conn.close()
                return
            
            # Unsubscribe
            success = remove_subscriber(db_conn._connection, chat_id)
            
            db_conn.close()
            
            if success:
                await update.message.reply_text(
                    "🔕 <b>Subscription disabled</b>\n\n"
                    "You will no longer receive automatic notifications.\n\n"
                    "To re-subscribe use /subscribe",
                    parse_mode=ParseMode.HTML
                )
            else:
                await update.message.reply_text(
                    "❌ Unsubscribe error. Please try later."
                )
                
        except Exception as e:
            print(f"❌ Unsubscribe error: {e}")
            await update.message.reply_text(
                "❌ An error occurred. Please try later."
            )
    
    async def mystatus_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Command /mystatus - check subscription status"""
        chat_id = update.effective_chat.id
        
        try:
            db_conn = get_db_connection()
            db_conn.connect()
            
            subscribed = is_subscribed(db_conn._connection, chat_id)
            stats = get_subscriber_stats(db_conn._connection)
            
            db_conn.close()
            
            if subscribed:
                status_message = f"""
✅ <b>Your status: Subscribed</b>

🔔 You receive automatic notifications about hot news (hotness ≥ {self.hotness_threshold}).

📊 <b>Notification settings:</b>
• Hotness threshold: {self.hotness_threshold}
• Check interval: {self.check_interval}s

To unsubscribe: /unsubscribe
                """
            else:
                status_message = f"""
🔕 <b>Your status: Not subscribed</b>

You are not receiving automatic notifications.

To subscribe: /subscribe
                """
            
            await update.message.reply_text(status_message.strip(), parse_mode=ParseMode.HTML)
            
        except Exception as e:
            print(f"❌ Status check error: {e}")
            await update.message.reply_text(
                "❌ An error occurred. Please try later."
            )
    
    async def top_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Command /top [limit] [hours]"""
        # Parse arguments
        args = context.args
        limit = 10
        hours = 24
        
        try:
            if len(args) >= 1:
                limit = min(max(int(args[0]), 1), 20)
            if len(args) >= 2:
                hours = min(max(int(args[1]), 1), 168)
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid format. Use: /top [count] [hours]"
            )
            return
        
        await update.message.reply_text(
            f"🔍 Fetching top {limit} news for last {hours}h..."
        )
        
        # Get news from DB
        news_list = self.get_top_news(limit, hours)
        
        if not news_list:
            await update.message.reply_text(
                f"📭 No news for the last {hours} hours"
            )
            return
        
        # Send each news item
        for i, news in enumerate(news_list, 1):
            message = self.format_news_message(news, i, len(news_list))
            
            # Add button for detailed analysis
            keyboard = [[
                InlineKeyboardButton(
                    "📊 Detailed Analysis", 
                    callback_data=f"analyze_{news['id']}"
                )
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                message,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )
    
    async def latest_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Command /latest [limit] - latest added news"""
        # Parse arguments
        args = context.args
        limit = 10
        
        try:
            if len(args) >= 1:
                limit = min(max(int(args[0]), 1), 20)
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid format. Use: /latest [count]"
            )
            return
        
        await update.message.reply_text(
            f"🔍 Fetching latest {limit} news..."
        )
        
        # Get news from DB
        news_list = self.get_latest_news(limit)
        
        if not news_list:
            await update.message.reply_text(
                "📭 No news in database"
            )
            return
        
        # Send each news item
        for i, news in enumerate(news_list, 1):
            message = self.format_latest_news_message(news, i, len(news_list))
            
            # Add button for detailed analysis
            keyboard = [[
                InlineKeyboardButton(
                    "📊 Detailed Analysis", 
                    callback_data=f"analyze_{news['id']}"
                )
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                message,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )
    
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Command /search [keywords] - search news by keywords"""
        # Parse arguments
        args = context.args
        
        if not args:
            await update.message.reply_text(
                "❌ Please specify keywords to search.\n\n"
                "<b>Examples:</b>\n"
                "<code>/search Bitcoin</code>\n"
                "<code>/search BTC ETH</code>\n"
                "<code>/search bull market</code>",
                parse_mode=ParseMode.HTML
            )
            return
        
        keywords = args
        keywords_str = ' '.join(keywords)
        
        await update.message.reply_text(
            f"🔍 Searching news by keywords: <b>{escape(keywords_str)}</b>",
            parse_mode=ParseMode.HTML
        )
        
        # Get news from DB
        news_list = self.search_news(keywords, limit=10)
        
        if not news_list:
            await update.message.reply_text(
                f"📭 No news found for query <b>{escape(keywords_str)}</b>.\n\n"
                "Try using different keywords.",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Send header with results count
        await update.message.reply_text(
            f"✅ Found <b>{len(news_list)}</b> news item(s)",
            parse_mode=ParseMode.HTML
        )
        
        # Send each news item
        for i, news in enumerate(news_list, 1):
            message = self.format_search_news_message(news, i, len(news_list), keywords_str)
            
            # Add button for detailed analysis
            keyboard = [[
                InlineKeyboardButton(
                    "📊 Detailed Analysis", 
                    callback_data=f"analyze_{news['id']}"
                )
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                message,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button presses"""
        query = update.callback_query
        await query.answer()
        
        if query.data.startswith("analyze_"):
            news_id = int(query.data.split("_")[1])
            
            await query.edit_message_text("⏳ Generating detailed analysis...")
            
            # Get news from DB
            news = self.get_news_by_id(news_id)
            if not news:
                await query.edit_message_text("❌ News not found")
                return
            
            # Generate analysis via LLM
            analysis = self.analyzer.generate_full_analysis({
                'headline': news['headline'],
                'content': news['content'],
                'tickers': news['tickers'],
                'hotness': news['ai_hotness'],
                'urls': news.get('urls', []),
                'published_at': news.get('published_time', ''),
                'source': news.get('source', 'Unknown source')
            })
            
            # Format and send (analysis now contains ready card)
            await query.edit_message_text(
                analysis.get('analysis_text', 'Analysis unavailable'),
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
    
    def get_top_news(self, limit: int, hours: int) -> List[Dict]:
        """Get top news from DB"""
        time_threshold = datetime.now() - timedelta(hours=hours)
        
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
                    lan.id_cluster,
                    sc.first_time,
                    sc.last_time,
                    sc.doc_count
                FROM llm_analyzed_news lan
                JOIN story_clusters sc ON lan.id_cluster = sc.id
                WHERE lan.published_time >= %s
                ORDER BY lan.ai_hotness DESC, lan.published_time DESC
                LIMIT %s
            """, (time_threshold, limit))
            
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
                    'first_time': row['first_time'],
                    'last_time': row['last_time'],
                    'doc_count': row['doc_count']
                })
            
            return news_list
    
    def get_latest_news(self, limit: int) -> List[Dict]:
        """Get latest added news from DB (by created_at)"""
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
                    lan.created_at,
                    lan.id_cluster,
                    sc.first_time,
                    sc.last_time,
                    sc.doc_count
                FROM llm_analyzed_news lan
                JOIN story_clusters sc ON lan.id_cluster = sc.id
                ORDER BY lan.created_at DESC
                LIMIT %s
            """, (limit,))
            
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
                    'created_at': row['created_at'],
                    'first_time': row['first_time'],
                    'last_time': row['last_time'],
                    'doc_count': row['doc_count']
                })
            
            return news_list
    
    def search_news(self, keywords: List[str], limit: int = 10) -> List[Dict]:
        """Search news by keywords in headline and content"""
        with get_db_cursor() as cursor:
            # Build OR conditions for each keyword
            # Use ~* operator (case-insensitive regex) for flexible matching
            # This allows partial matches anywhere in the text
            conditions = []
            params = []
            
            for keyword in keywords:
                # Escape special regex characters and create pattern
                # ~* is PostgreSQL's case-insensitive regex operator
                conditions.append("(lan.headline ~* %s OR lan.content ~* %s)")
                params.extend([keyword, keyword])
            
            where_clause = " OR ".join(conditions)
            params.append(limit)
            
            query = f"""
                SELECT 
                    lan.id,
                    lan.headline,
                    lan.content,
                    lan.ai_hotness,
                    lan.tickers_json,
                    lan.urls_json,
                    lan.published_time,
                    lan.created_at,
                    lan.id_cluster,
                    sc.first_time,
                    sc.last_time,
                    sc.doc_count
                FROM llm_analyzed_news lan
                JOIN story_clusters sc ON lan.id_cluster = sc.id
                WHERE {where_clause}
                ORDER BY lan.published_time DESC
                LIMIT %s
            """
            
            cursor.execute(query, tuple(params))
            
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
                    'created_at': row['created_at'],
                    'first_time': row['first_time'],
                    'last_time': row['last_time'],
                    'doc_count': row['doc_count']
                })
            
            return news_list
    
    def get_news_by_id(self, news_id: int) -> Dict:
        """Get news by ID"""
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    lan.id,
                    lan.headline,
                    lan.content,
                    lan.ai_hotness,
                    lan.tickers_json,
                    lan.urls_json,
                    lan.published_time
                FROM llm_analyzed_news lan
                WHERE lan.id = %s
            """, (news_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return {
                'id': row['id'],
                'headline': row['headline'],
                'content': row['content'],
                'ai_hotness': row['ai_hotness'],
                'tickers': json.loads(row['tickers_json']) if row['tickers_json'] else [],
                'urls': json.loads(row['urls_json']) if row['urls_json'] else []
            }
    
    def format_news_message(self, news: Dict, index: int, total: int) -> str:
        """Format news message"""
        hotness = news['ai_hotness']
        hotness_emoji = self._get_hotness_emoji(hotness)
        
        # Escape for HTML
        headline_escaped = escape(news['headline'])
        
        # Tickers
        tickers_list = news.get('tickers', [])
        tickers_str = escape(', '.join(tickers_list)) if tickers_list else '—'
        
        # Links (max 3)
        urls = news.get('urls', [])[:3]
        if urls:
            sources_list = []
            for url in urls:
                # Limit URL length for display
                display_url = url if len(url) < 50 else url[:47] + '...'
                sources_list.append(f'• <a href="{url}">{escape(display_url)}</a>')
            sources_str = '\n'.join(sources_list)
        else:
            sources_str = '—'
        
        # Timeline
        first_time = news.get('first_time')
        last_time = news.get('last_time')
        timeline = f"First mention: {first_time.strftime('%d.%m %H:%M')}"
        if first_time != last_time:
            timeline += f"\nLast: {last_time.strftime('%d.%m %H:%M')}"
        
        message = f"""
{hotness_emoji} <b>#{index}/{total} News</b>

<b>{headline_escaped}</b>

🔥 <b>Hotness:</b> {hotness:.2f}/1.00
📊 <b>Tickers:</b> {tickers_str}
📄 <b>Documents:</b> {news.get('doc_count', 1)}

⏰ <b>Timeline:</b>
{timeline}

🔗 <b>Sources:</b>
{sources_str}
        """.strip()
        
        return message
    
    def format_latest_news_message(self, news: Dict, index: int, total: int) -> str:
        """Format message for latest news"""
        hotness = news['ai_hotness']
        hotness_emoji = self._get_hotness_emoji(hotness)
        
        # Escape for HTML
        headline_escaped = escape(news['headline'])
        
        # Tickers
        tickers_list = news.get('tickers', [])
        tickers_str = escape(', '.join(tickers_list)) if tickers_list else '—'
        
        # Links (max 3)
        urls = news.get('urls', [])[:3]
        if urls:
            sources_list = []
            for url in urls:
                display_url = url if len(url) < 50 else url[:47] + '...'
                sources_list.append(f'• <a href="{url}">{escape(display_url)}</a>')
            sources_str = '\n'.join(sources_list)
        else:
            sources_str = '—'
        
        # Time added to system
        created_at = news.get('created_at')
        created_str = created_at.strftime('%d.%m.%Y %H:%M') if created_at else '—'
        
        # Original publication time
        published_time = news.get('published_time')
        published_str = published_time.strftime('%d.%m.%Y %H:%M') if published_time else '—'
        
        message = f"""
{hotness_emoji} <b>#{index}/{total} News</b>

<b>{headline_escaped}</b>

🔥 <b>Hotness:</b> {hotness:.2f}/1.00
📊 <b>Tickers:</b> {tickers_str}
📄 <b>Documents:</b> {news.get('doc_count', 1)}

⏰ <b>Added to system:</b> {created_str}
📅 <b>Published:</b> {published_str}

🔗 <b>Sources:</b>
{sources_str}
        """.strip()
        
        return message
    
    def format_search_news_message(self, news: Dict, index: int, total: int, keywords: str) -> str:
        """Format message for search results"""
        hotness = news['ai_hotness']
        hotness_emoji = self._get_hotness_emoji(hotness)
        
        # Escape for HTML
        headline_escaped = escape(news['headline'])
        
        # Tickers
        tickers_list = news.get('tickers', [])
        tickers_str = escape(', '.join(tickers_list)) if tickers_list else '—'
        
        # Links (max 3)
        urls = news.get('urls', [])[:3]
        if urls:
            sources_list = []
            for url in urls:
                display_url = url if len(url) < 50 else url[:47] + '...'
                sources_list.append(f'• <a href="{url}">{escape(display_url)}</a>')
            sources_str = '\n'.join(sources_list)
        else:
            sources_str = '—'
        
        # Publication time
        published_time = news.get('published_time')
        published_str = published_time.strftime('%d.%m.%Y %H:%M') if published_time else '—'
        
        message = f"""
🔍 <b>#{index}/{total} Search Result</b>

<b>{headline_escaped}</b>

🔥 <b>Hotness:</b> {hotness:.2f}/1.00
📊 <b>Tickers:</b> {tickers_str}
📄 <b>Documents:</b> {news.get('doc_count', 1)}
📅 <b>Published:</b> {published_str}

🔗 <b>Sources:</b>
{sources_str}
        """.strip()
        
        return message
    
    def format_detailed_analysis(self, news: Dict, analysis: Dict) -> str:
        """Format detailed analysis (now returns ready card)"""
        # analysis already contains ready card in Markdown format
        return analysis.get('analysis_text', 'Analysis unavailable')
    
    def _get_hotness_emoji(self, hotness: float) -> str:
        """Emoji based on hotness"""
        if hotness >= 0.8:
            return "🔴🔥"
        elif hotness >= 0.6:
            return "🟠🔥"
        elif hotness >= 0.4:
            return "🟡"
        else:
            return "🟢"
    
    async def monitor_hot_news(self):
        """Background task for monitoring hot news"""
        print(f"🔍 Hot news monitor started (threshold: {self.hotness_threshold})")
        
        while True:
            try:
                # Get list of active subscribers
                db_conn = get_db_connection()
                db_conn.connect()
                subscribers = get_active_subscribers(db_conn._connection)
                db_conn.close()
                
                if not subscribers:
                    print("ℹ️ No active subscribers")
                    await asyncio.sleep(self.check_interval)
                    continue
                
                print(f"📊 Active subscribers: {len(subscribers)}")
                
                # Get hot news
                hot_news = self.get_hot_news_for_monitor()
                
                for news in hot_news:
                    if news['id'] in self.notified_news:
                        continue
                    
                    print(f"🔥 Sending notification: {news['headline'][:50]}...")
                    
                    try:
                        # Generate analysis once for all subscribers
                        analysis = self.analyzer.generate_full_analysis({
                            'headline': news['headline'],
                            'content': news['content'],
                            'tickers': news['tickers'],
                            'hotness': news['ai_hotness'],
                            'urls': news.get('urls', []),
                            'published_at': news.get('published_time', ''),
                            'source': news.get('source', 'Unknown source')
                        })
                        
                        # Format message (add alert header)
                        message = self.format_hot_news_alert(news, analysis)
                        
                        # Send to all subscribers
                        sent_count = 0
                        failed_count = 0
                        
                        for chat_id in subscribers:
                            try:
                                await self.app.bot.send_message(
                                    chat_id=chat_id,
                                    text=message,
                                    parse_mode=ParseMode.MARKDOWN,
                                    disable_web_page_preview=True
                                )
                                sent_count += 1
                                
                                # Update last notification time
                                db_conn = get_db_connection()
                                db_conn.connect()
                                update_last_notification(db_conn._connection, chat_id)
                                db_conn.close()
                                
                                await asyncio.sleep(0.1)  # Small delay between sends
                                
                            except Exception as e:
                                print(f"  ❌ Send error chat_id {chat_id}: {e}")
                                failed_count += 1
                        
                        self.notified_news.add(news['id'])
                        print(f"  ✅ Sent: {sent_count}, Errors: {failed_count}")
                        
                        await asyncio.sleep(2)
                        
                    except Exception as e:
                        print(f"❌ News processing error: {e}")
                
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                print(f"❌ Monitor error: {e}")
                await asyncio.sleep(self.check_interval)
    
    def get_hot_news_for_monitor(self):
        """Get only NEW hot news (created in last check_interval * 2)"""
        with get_db_cursor() as cursor:
            # Look for news created in last 2 check intervals (for reliability)
            # This ensures we don't miss news and don't send duplicates
            cursor.execute("""
                SELECT 
                    lan.id,
                    lan.headline,
                    lan.content,
                    lan.ai_hotness,
                    lan.tickers_json,
                    lan.urls_json,
                    lan.published_time,
                    lan.created_at,
                    sc.doc_count,
                    sc.first_time,
                    sc.last_time
                FROM llm_analyzed_news lan
                JOIN story_clusters sc ON lan.id_cluster = sc.id
                WHERE lan.ai_hotness >= %s
                    AND lan.created_at >= NOW() - INTERVAL '%s seconds'
                ORDER BY lan.created_at DESC
                LIMIT 20
            """, (self.hotness_threshold, self.check_interval * 2))
            
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
    
    async def post_init(self, application):
        """Initialization after bot startup"""
        if self.enable_monitor:
            # Start monitor as background task
            asyncio.create_task(self.monitor_hot_news())
            print(f"🔍 Auto-notifications enabled (threshold: {self.hotness_threshold}, interval: {self.check_interval}s)")
    
    def run(self):
        """Run bot"""
        print("🤖 Telegram bot started...")
        
        # Register post_init callback
        self.app.post_init = self.post_init
        
        try:
            self.app.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
                close_loop=False
            )
        except Exception as e:
            print(f"❌ Bot startup error: {e}")
            print("Check:")
            print("1. TELEGRAM_BOT_TOKEN is correct in .env")
            print("2. Internet connection")
            print("3. Telegram API availability")
            raise

