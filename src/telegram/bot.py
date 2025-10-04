"""Telegram бот для отправки новостей"""
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv

from ..database import get_db_cursor
from .news_analyzer import NewsAnalyzer

load_dotenv()


class NewsBot:
    """Telegram бот для новостей"""
    
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN не установлен в .env")
        
        self.analyzer = NewsAnalyzer()
        self.app = Application.builder().token(self.token).build()
        
        # Регистрируем команды
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("top", self.top_command))
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        welcome_message = """
🔥 *Добро пожаловать в AiAlphaPulse!*

Я помогу отслеживать самые горячие финансовые новости.

📊 *Доступные команды:*
/top - Топ новостей (с параметрами)
/help - Справка

📌 *Примеры:*
`/top 10 24` - Топ-10 за 24 часа
`/top 5 48` - Топ-5 за 48 часов
`/top` - Топ-10 за 24 часа (по умолчанию)

🔔 *Автоуведомления:*
Горячие новости (hotness ≥ 0.7) приходят автоматически!
        """
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        help_text = """
📖 *Справка по командам*

*Формат:* `/top [количество] [часы]`

*Параметры:*
• количество - сколько новостей (1-20, default: 10)
• часы - за какой период (1-168, default: 24)

*Примеры:*
`/top` - Топ-10 за последние 24 часа
`/top 5` - Топ-5 за последние 24 часа  
`/top 15 48` - Топ-15 за последние 48 часов
`/top 20 72` - Топ-20 за последние 3 дня

📊 *Что показывается:*
• Заголовок новости
• Оценка горячести (0-1)
• Почему важно сейчас
• Тикеры/активы
• Ссылки на источники
• Временная шкала
• Черновик анализа

🔥 *Для особо горячих новостей* (≥0.7):
• Торговый сигнал
• Рекомендации по активам
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def top_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /top [limit] [hours]"""
        # Парсим аргументы
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
                "❌ Неверный формат. Используйте: /top [количество] [часы]"
            )
            return
        
        await update.message.reply_text(
            f"🔍 Получаю топ-{limit} новостей за последние {hours}ч..."
        )
        
        # Получаем новости из БД
        news_list = self.get_top_news(limit, hours)
        
        if not news_list:
            await update.message.reply_text(
                f"📭 Нет новостей за последние {hours} часов"
            )
            return
        
        # Отправляем каждую новость
        for i, news in enumerate(news_list, 1):
            message = self.format_news_message(news, i, len(news_list))
            
            # Добавляем кнопку для детального анализа
            keyboard = [[
                InlineKeyboardButton(
                    "📊 Детальный анализ", 
                    callback_data=f"analyze_{news['id']}"
                )
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатий на кнопки"""
        query = update.callback_query
        await query.answer()
        
        if query.data.startswith("analyze_"):
            news_id = int(query.data.split("_")[1])
            
            await query.edit_message_text("⏳ Генерирую детальный анализ...")
            
            # Получаем новость из БД
            news = self.get_news_by_id(news_id)
            if not news:
                await query.edit_message_text("❌ Новость не найдена")
                return
            
            # Генерируем анализ через LLM
            analysis = self.analyzer.generate_full_analysis({
                'headline': news['headline'],
                'content': news['content'],
                'tickers': news['tickers'],
                'hotness': news['ai_hotness']
            })
            
            # Форматируем и отправляем
            detail_message = self.format_detailed_analysis(news, analysis)
            await query.edit_message_text(
                detail_message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
    
    def get_top_news(self, limit: int, hours: int) -> List[Dict]:
        """Получить топ новостей из БД"""
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
    
    def get_news_by_id(self, news_id: int) -> Dict:
        """Получить новость по ID"""
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
        """Форматирование сообщения с новостью"""
        hotness = news['ai_hotness']
        hotness_emoji = self._get_hotness_emoji(hotness)
        
        # Тикеры
        tickers_str = ', '.join(news['tickers']) if news['tickers'] else '—'
        
        # Ссылки (макс 3)
        urls = news.get('urls', [])[:3]
        sources_str = '\n'.join([f"• {url}" for url in urls]) if urls else '—'
        
        # Timeline
        first_time = news.get('first_time')
        last_time = news.get('last_time')
        timeline = f"Первое упоминание: {first_time.strftime('%d.%m %H:%M')}"
        if first_time != last_time:
            timeline += f"\nПоследнее: {last_time.strftime('%d.%m %H:%M')}"
        
        message = f"""
{hotness_emoji} *#{index}/{total} Новость*

*{news['headline']}*

🔥 *Hotness:* {hotness:.2f}/1.00
📊 *Тикеры:* {tickers_str}
📄 *Документов:* {news.get('doc_count', 1)}

⏰ *Timeline:*
{timeline}

🔗 *Источники:*
{sources_str}
        """.strip()
        
        return message
    
    def format_detailed_analysis(self, news: Dict, analysis: Dict) -> str:
        """Форматирование детального анализа"""
        hotness = news['ai_hotness']
        hotness_emoji = self._get_hotness_emoji(hotness)
        
        message = f"""
{hotness_emoji} *ДЕТАЛЬНЫЙ АНАЛИЗ*

*{news['headline']}*

🔥 *Hotness:* {hotness:.2f}/1.00

💡 *Почему важно сейчас:*
{analysis.get('why_now', 'Анализ формируется...')}

📝 *Черновик анализа:*
{analysis.get('draft', 'Детали формируются...')}
        """.strip()
        
        # Добавляем торговый сигнал для горячих новостей
        if hotness >= 0.7 and 'trading_signal' in analysis:
            message += f"\n\n🎯 *ТОРГОВЫЙ СИГНАЛ:*\n{analysis['trading_signal']}"
        
        return message
    
    def _get_hotness_emoji(self, hotness: float) -> str:
        """Эмодзи в зависимости от горячности"""
        if hotness >= 0.8:
            return "🔴🔥"
        elif hotness >= 0.6:
            return "🟠🔥"
        elif hotness >= 0.4:
            return "🟡"
        else:
            return "🟢"
    
    def run(self):
        """Запуск бота"""
        print("🤖 Telegram бот запущен...")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)

