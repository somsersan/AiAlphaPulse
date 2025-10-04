"""Telegram бот для отправки новостей"""
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
    """Telegram бот для новостей"""
    
    def __init__(self, enable_monitor: bool = True, hotness_threshold: float = 0.7, check_interval: int = 60):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN не установлен в .env")
        
        self.analyzer = NewsAnalyzer()
        self.app = Application.builder().token(self.token).build()
        
        # Регистрируем команды
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("top", self.top_command))
        self.app.add_handler(CommandHandler("latest", self.latest_command))
        self.app.add_handler(CommandHandler("subscribe", self.subscribe_command))
        self.app.add_handler(CommandHandler("unsubscribe", self.unsubscribe_command))
        self.app.add_handler(CommandHandler("mystatus", self.mystatus_command))
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Инициализируем таблицу подписчиков
        self._init_subscribers_table()
        
        # Настройки монитора горячих новостей
        self.enable_monitor = enable_monitor
        self.hotness_threshold = hotness_threshold
        self.check_interval = check_interval
        self.notified_news: Set[int] = set()
        
        # TELEGRAM_CHAT_ID теперь не обязателен - используем подписчиков из БД
        self.legacy_chat_id = os.getenv('TELEGRAM_CHAT_ID')  # Для обратной совместимости
    
    def _init_subscribers_table(self):
        """Инициализировать таблицу подписчиков"""
        try:
            db_conn = get_db_connection()
            db_conn.connect()
            create_subscribers_table(db_conn._connection)
            
            # Если есть legacy TELEGRAM_CHAT_ID, добавим его как подписчика
            if self.legacy_chat_id:
                try:
                    chat_id = int(self.legacy_chat_id)
                    add_subscriber(db_conn._connection, chat_id, username="legacy_user")
                    print(f"✅ Legacy chat_id {chat_id} добавлен в подписчики")
                except:
                    pass
            
            db_conn.close()
        except Exception as e:
            print(f"⚠️ Ошибка инициализации таблицы подписчиков: {e}")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        welcome_message = """
🔥 <b>Добро пожаловать в AiAlphaPulse!</b>

Я помогу отслеживать самые горячие финансовые новости.

📊 <b>Доступные команды:</b>
/top - Топ новостей по hotness
/latest - Последние добавленные новости
/subscribe - Подписаться на уведомления
/unsubscribe - Отписаться от уведомлений
/mystatus - Проверить статус подписки
/help - Справка

📌 <b>Примеры:</b>
<code>/top 10 24</code> - Топ-10 за 24 часа
<code>/top 5 48</code> - Топ-5 за 48 часов
<code>/latest 5</code> - Последние 5 новостей
<code>/latest</code> - Последние 10 новостей

🔔 <b>Автоуведомления:</b>
Подпишитесь командой /subscribe чтобы получать горячие новости (hotness ≥ 0.7) автоматически!
        """
        await update.message.reply_text(welcome_message, parse_mode=ParseMode.HTML)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        help_text = """
📖 <b>Справка по командам</b>

<b>1️⃣ Топ по hotness:</b>
<code>/top [количество] [часы]</code>
• количество - сколько новостей (1-20, default: 10)
• часы - за какой период (1-168, default: 24)

<b>Примеры:</b>
<code>/top</code> - Топ-10 за последние 24 часа
<code>/top 5</code> - Топ-5 за последние 24 часа  
<code>/top 15 48</code> - Топ-15 за последние 48 часов

<b>2️⃣ Последние новости:</b>
<code>/latest [количество]</code>
• количество - сколько новостей (1-20, default: 10)

<b>Примеры:</b>
<code>/latest</code> - Последние 10 новостей
<code>/latest 5</code> - Последние 5 новостей
<code>/latest 20</code> - Последние 20 новостей

📊 <b>Что показывается:</b>
• Заголовок новости
• Оценка горячести (0-1)
• Тикеры/активы
• Ссылки на источники
• Время публикации
• Кнопка для детального анализа

🔥 <b>Для особо горячих новостей</b> (≥0.7):
• Торговый сигнал
• Рекомендации по активам
        """
        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)
    
    async def subscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /subscribe - подписаться на уведомления"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        try:
            db_conn = get_db_connection()
            db_conn.connect()
            
            # Проверяем, уже подписан ли
            if is_subscribed(db_conn._connection, chat_id):
                await update.message.reply_text(
                    "✅ Вы уже подписаны на уведомления о горячих новостях!"
                )
                db_conn.close()
                return
            
            # Добавляем подписчика
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
                    "🔔 <b>Подписка активирована!</b>\n\n"
                    "Теперь вы будете получать уведомления о горячих новостях (hotness ≥ 0.7).\n\n"
                    "Для отписки используйте /unsubscribe",
                    parse_mode=ParseMode.HTML
                )
            else:
                await update.message.reply_text(
                    "❌ Ошибка подписки. Попробуйте позже."
                )
                
        except Exception as e:
            print(f"❌ Ошибка подписки: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка. Попробуйте позже."
            )
    
    async def unsubscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /unsubscribe - отписаться от уведомлений"""
        chat_id = update.effective_chat.id
        
        try:
            db_conn = get_db_connection()
            db_conn.connect()
            
            # Проверяем, подписан ли
            if not is_subscribed(db_conn._connection, chat_id):
                await update.message.reply_text(
                    "ℹ️ Вы не подписаны на уведомления.\n\n"
                    "Для подписки используйте /subscribe"
                )
                db_conn.close()
                return
            
            # Отписываем
            success = remove_subscriber(db_conn._connection, chat_id)
            
            db_conn.close()
            
            if success:
                await update.message.reply_text(
                    "🔕 <b>Подписка отключена</b>\n\n"
                    "Вы больше не будете получать автоматические уведомления.\n\n"
                    "Для возобновления используйте /subscribe",
                    parse_mode=ParseMode.HTML
                )
            else:
                await update.message.reply_text(
                    "❌ Ошибка отписки. Попробуйте позже."
                )
                
        except Exception as e:
            print(f"❌ Ошибка отписки: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка. Попробуйте позже."
            )
    
    async def mystatus_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /mystatus - проверить статус подписки"""
        chat_id = update.effective_chat.id
        
        try:
            db_conn = get_db_connection()
            db_conn.connect()
            
            subscribed = is_subscribed(db_conn._connection, chat_id)
            stats = get_subscriber_stats(db_conn._connection)
            
            db_conn.close()
            
            if subscribed:
                status_message = f"""
✅ <b>Ваш статус: Подписан</b>

🔔 Вы получаете автоматические уведомления о горячих новостях (hotness ≥ {self.hotness_threshold}).

📊 <b>Настройки уведомлений:</b>
• Порог hotness: {self.hotness_threshold}
• Интервал проверки: {self.check_interval}с

Для отписки: /unsubscribe
                """
            else:
                status_message = f"""
🔕 <b>Ваш статус: Не подписан</b>

Вы не получаете автоматические уведомления.

Для подписки: /subscribe
                """
            
            await update.message.reply_text(status_message.strip(), parse_mode=ParseMode.HTML)
            
        except Exception as e:
            print(f"❌ Ошибка проверки статуса: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка. Попробуйте позже."
            )
    
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
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )
    
    async def latest_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /latest [limit] - последние добавленные новости"""
        # Парсим аргументы
        args = context.args
        limit = 10
        
        try:
            if len(args) >= 1:
                limit = min(max(int(args[0]), 1), 20)
        except ValueError:
            await update.message.reply_text(
                "❌ Неверный формат. Используйте: /latest [количество]"
            )
            return
        
        await update.message.reply_text(
            f"🔍 Получаю последние {limit} новостей..."
        )
        
        # Получаем новости из БД
        news_list = self.get_latest_news(limit)
        
        if not news_list:
            await update.message.reply_text(
                "📭 Нет новостей в базе данных"
            )
            return
        
        # Отправляем каждую новость
        for i, news in enumerate(news_list, 1):
            message = self.format_latest_news_message(news, i, len(news_list))
            
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
                parse_mode=ParseMode.HTML,
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
                parse_mode=ParseMode.MARKDOWN,
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
    
    def get_latest_news(self, limit: int) -> List[Dict]:
        """Получить последние добавленные новости из БД (по created_at)"""
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
        
        # Экранируем для HTML
        headline_escaped = escape(news['headline'])
        
        # Тикеры
        tickers_list = news.get('tickers', [])
        tickers_str = escape(', '.join(tickers_list)) if tickers_list else '—'
        
        # Ссылки (макс 3)
        urls = news.get('urls', [])[:3]
        if urls:
            sources_list = []
            for url in urls:
                # Ограничиваем длину URL для отображения
                display_url = url if len(url) < 50 else url[:47] + '...'
                sources_list.append(f'• <a href="{url}">{escape(display_url)}</a>')
            sources_str = '\n'.join(sources_list)
        else:
            sources_str = '—'
        
        # Timeline
        first_time = news.get('first_time')
        last_time = news.get('last_time')
        timeline = f"Первое упоминание: {first_time.strftime('%d.%m %H:%M')}"
        if first_time != last_time:
            timeline += f"\nПоследнее: {last_time.strftime('%d.%m %H:%M')}"
        
        message = f"""
{hotness_emoji} <b>#{index}/{total} Новость</b>

<b>{headline_escaped}</b>

🔥 <b>Hotness:</b> {hotness:.2f}/1.00
📊 <b>Тикеры:</b> {tickers_str}
📄 <b>Документов:</b> {news.get('doc_count', 1)}

⏰ <b>Timeline:</b>
{timeline}

🔗 <b>Источники:</b>
{sources_str}
        """.strip()
        
        return message
    
    def format_latest_news_message(self, news: Dict, index: int, total: int) -> str:
        """Форматирование сообщения для последних новостей"""
        hotness = news['ai_hotness']
        hotness_emoji = self._get_hotness_emoji(hotness)
        
        # Экранируем для HTML
        headline_escaped = escape(news['headline'])
        
        # Тикеры
        tickers_list = news.get('tickers', [])
        tickers_str = escape(', '.join(tickers_list)) if tickers_list else '—'
        
        # Ссылки (макс 3)
        urls = news.get('urls', [])[:3]
        if urls:
            sources_list = []
            for url in urls:
                display_url = url if len(url) < 50 else url[:47] + '...'
                sources_list.append(f'• <a href="{url}">{escape(display_url)}</a>')
            sources_str = '\n'.join(sources_list)
        else:
            sources_str = '—'
        
        # Время добавления в систему
        created_at = news.get('created_at')
        created_str = created_at.strftime('%d.%m.%Y %H:%M') if created_at else '—'
        
        # Время публикации оригинала
        published_time = news.get('published_time')
        published_str = published_time.strftime('%d.%m.%Y %H:%M') if published_time else '—'
        
        message = f"""
{hotness_emoji} <b>#{index}/{total} Новость</b>

<b>{headline_escaped}</b>

🔥 <b>Hotness:</b> {hotness:.2f}/1.00
📊 <b>Тикеры:</b> {tickers_str}
📄 <b>Документов:</b> {news.get('doc_count', 1)}

⏰ <b>Добавлено в систему:</b> {created_str}
📅 <b>Опубликовано:</b> {published_str}

🔗 <b>Источники:</b>
{sources_str}
        """.strip()
        
        return message
    
    def format_detailed_analysis(self, news: Dict, analysis: Dict) -> str:
        """Форматирование детального анализа"""
        hotness = news['ai_hotness']
        hotness_emoji = self._get_hotness_emoji(hotness)
        
        # Для детального анализа используем Markdown с моноширинным шрифтом
        message = f"""
{hotness_emoji} *ДЕТАЛЬНЫЙ АНАЛИЗ*

*{news['headline']}*

🔥 *Hotness:* {hotness:.2f}/1.00

💡 *Почему важно сейчас:*
{analysis.get('why_now', 'Анализ формируется...')}

📝 *Черновик анализа:*
```
{analysis.get('draft', 'Детали формируются...')}
```
        """.strip()
        
        # Добавляем торговый сигнал для горячих новостей
        if hotness >= 0.7 and 'trading_signal' in analysis:
            message += f"\n\n🎯 *ТОРГОВЫЙ СИГНАЛ:*\n```\n{analysis['trading_signal']}\n```"
        
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
    
    async def monitor_hot_news(self):
        """Фоновая задача мониторинга горячих новостей"""
        print(f"🔍 Монитор горячих новостей запущен (порог: {self.hotness_threshold})")
        
        while True:
            try:
                # Получаем список активных подписчиков
                db_conn = get_db_connection()
                db_conn.connect()
                subscribers = get_active_subscribers(db_conn._connection)
                db_conn.close()
                
                if not subscribers:
                    print("ℹ️ Нет активных подписчиков")
                    await asyncio.sleep(self.check_interval)
                    continue
                
                print(f"📊 Активных подписчиков: {len(subscribers)}")
                
                # Получаем горячие новости
                hot_news = self.get_hot_news_for_monitor()
                
                for news in hot_news:
                    if news['id'] in self.notified_news:
                        continue
                    
                    print(f"🔥 Отправляем уведомление: {news['headline'][:50]}...")
                    
                    try:
                        # Генерируем анализ один раз для всех подписчиков
                        analysis = self.analyzer.generate_full_analysis({
                            'headline': news['headline'],
                            'content': news['content'],
                            'tickers': news['tickers'],
                            'hotness': news['ai_hotness']
                        })
                        
                        # Форматируем сообщение
                        message = self.format_hot_news_alert(news, analysis)
                        
                        # Отправляем всем подписчикам
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
                                
                                # Обновляем время последнего уведомления
                                db_conn = get_db_connection()
                                db_conn.connect()
                                update_last_notification(db_conn._connection, chat_id)
                                db_conn.close()
                                
                                await asyncio.sleep(0.1)  # Небольшая задержка между отправками
                                
                            except Exception as e:
                                print(f"  ❌ Ошибка отправки chat_id {chat_id}: {e}")
                                failed_count += 1
                        
                        self.notified_news.add(news['id'])
                        print(f"  ✅ Отправлено: {sent_count}, Ошибок: {failed_count}")
                        
                        await asyncio.sleep(2)
                        
                    except Exception as e:
                        print(f"❌ Ошибка обработки новости: {e}")
                
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                print(f"❌ Ошибка в мониторе: {e}")
                await asyncio.sleep(self.check_interval)
    
    def get_hot_news_for_monitor(self):
        """Получить только НОВЫЕ горячие новости (созданные за последний check_interval * 2)"""
        with get_db_cursor() as cursor:
            # Ищем новости, созданные за последние 2 интервала проверки (для надёжности)
            # Это гарантирует, что мы не пропустим новости и не будем слать повторы
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
        """Форматирование алерта о горячей новости"""
        hotness = news['ai_hotness']
        tickers_str = ', '.join(news['tickers']) if news['tickers'] else 'не указаны'
        
        urls = news.get('urls', [])[:3]
        sources_str = '\n'.join([f"• {url}" for url in urls]) if urls else 'нет'
        
        first_time = news.get('first_time')
        last_time = news.get('last_time')
        timeline = f"Первое: {first_time.strftime('%d.%m %H:%M')}"
        if first_time != last_time:
            timeline += f"\nПоследнее: {last_time.strftime('%d.%m %H:%M')}"
        
        message = f"""
🚨 *ГОРЯЧАЯ НОВОСТЬ!*
🔥 *Hotness: {hotness:.2f}/1.00*

*{news['headline']}*

💡 *Почему важно сейчас:*
{analysis.get('why_now', 'Формируется анализ...')}

📊 *Тикеры:* {tickers_str}
📄 *Документов:* {news.get('doc_count', 1)}

⏰ *Timeline:*
{timeline}

📝 *Черновик анализа:*
```
{analysis.get('draft', 'Детали формируются...')}
```
        """.strip()
        
        # Добавляем торговый сигнал если есть
        if 'trading_signal' in analysis:
            message += f"\n\n🎯 *ТОРГОВЫЙ СИГНАЛ:*\n```\n{analysis['trading_signal']}\n```"
        
        message += f"\n\n🔗 *Источники:*\n{sources_str}"
        
        return message
    
    async def post_init(self, application):
        """Инициализация после запуска бота"""
        if self.enable_monitor:
            # Запускаем монитор как фоновую задачу
            asyncio.create_task(self.monitor_hot_news())
            print(f"🔍 Автоуведомления включены (порог: {self.hotness_threshold}, интервал: {self.check_interval}с)")
    
    def run(self):
        """Запуск бота"""
        print("🤖 Telegram бот запущен...")
        
        # Регистрируем post_init callback
        self.app.post_init = self.post_init
        
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)

