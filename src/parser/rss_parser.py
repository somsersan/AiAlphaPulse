import feedparser
import requests
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
from dotenv import load_dotenv
import re
import time
import os


    # # Investopedia (Все статьи)
    # 'https://news.google.com/rss?hl=ru&gl=RU&ceid=RU:ru',
    # 'https://www.investopedia.com/rss-feed-4790074',
RSS_URLS = [
    # ----------------------------------------------------
    # РОССИЙСКИЕ ФИНАНСОВЫЕ ИСТОЧНИКИ
    # ----------------------------------------------------
    "https://smart-lab.ru/news/rss/",
    "https://smart-lab.ru/forum/rss/",
    'https://tass.ru/rss/v2.xml',  # ТАСС
    'http://static.feed.rbc.ru/rbc/logical/footer/news.rss',  # РБК
    'https://www.vedomosti.ru/rss/news',  # Ведомости
    'https://www.kommersant.ru/RSS/news.xml',  # Коммерсантъ
    'https://www.kommersant.ru/RSS/finance.xml',  # Коммерсантъ Финансы
    'https://lenta.ru/rss/news',  # Лента.ру
    
    # ----------------------------------------------------
    # ГЛОБАЛЬНЫЕ ФИНАНСОВЫЕ ИСТОЧНИКИ
    # ----------------------------------------------------
    'https://feeds.bloomberg.com/markets/news.rss',  # Bloomberg Markets
    'https://feeds.bloomberg.com/business/news.rss',  # Bloomberg Business
    'https://www.cnbc.com/id/100003114/device/rss/rss.html',  # CNBC
    'https://www.businessinsider.com/rss',  # Business Insider
    'https://www.ft.com/?format=rss',  # Financial Times
    'https://fortune.com/feed',  # Fortune
    'https://www.investing.com/rss/news.rss',  # Investing.com
    'https://finance.yahoo.com/news/rssindex',  # Yahoo Finance
    'https://financialpost.com/feed',  # Financial Post
]

# PostgreSQL настройки
load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://admin:04102025@130.193.55.244:5432/alphapulse')

# --- 2. Определение модели БД (SQLAlchemy) ---
Base = declarative_base()

class Article(Base):
    __tablename__ = 'articles'
    
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False, unique=True)
    link = Column(String, nullable=False)
    published = Column(DateTime)
    summary = Column(Text)
    source = Column(String)
    feed_url = Column(String)
    content = Column(Text)  # Полный текст статьи
    author = Column(String)  # Автор статьи
    category = Column(String)  # Категория/теги
    image_url = Column(String)  # URL изображения
    word_count = Column(Integer)  # Количество слов
    reading_time = Column(Integer)  # Время чтения в минутах
    is_processed = Column(Boolean, default=False)  # Обработана ли статья
    created_at = Column(DateTime, default=datetime.now)  # Когда добавлена в БД

    def __repr__(self):
        return f"<Article(title='{self.title[:30]}...', source='{self.source}')>"

# --- 3. Функции парсинга и сохранения ---

def extract_full_content(article_url, max_retries=3):
    """Извлекает полный текст статьи по URL."""
    for attempt in range(max_retries):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(article_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Удаляем ненужные элементы
            for script in soup(["script", "style", "nav", "footer", "aside"]):
                script.decompose()
            
            # Ищем основной контент по различным селекторам
            content_selectors = [
                'article', '.article-content', '.post-content', '.entry-content',
                '.content', '.main-content', '.story-content', '.news-content',
                '[role="main"]', '.article-body', '.post-body'
            ]
            
            content = None
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    content = content_elem.get_text(strip=True)
                    break
            
            if not content:
                # Если не нашли специальный контейнер, берем body
                body = soup.find('body')
                if body:
                    content = body.get_text(strip=True)
            
            return content[:5000] if content else None  # Ограничиваем размер
            
        except Exception as e:
            print(f"   ⚠️ Ошибка при извлечении контента (попытка {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2)  # Пауза перед повтором
            continue
    
    return None

def extract_article_metadata(entry):
    """Извлекает дополнительные метаданные из RSS-записи."""
    metadata = {
        'author': None,
        'category': None,
        'image_url': None
    }
    
    # Автор
    if hasattr(entry, 'author'):
        metadata['author'] = entry.author
    elif hasattr(entry, 'author_detail') and hasattr(entry.author_detail, 'name'):
        metadata['author'] = entry.author_detail.name
    
    # Категория/теги
    if hasattr(entry, 'tags') and entry.tags:
        categories = [tag.term for tag in entry.tags if hasattr(tag, 'term')]
        metadata['category'] = ', '.join(categories[:3])  # Берем первые 3 тега
    
    # Изображение
    if hasattr(entry, 'media_content') and entry.media_content:
        for media in entry.media_content:
            if hasattr(media, 'type') and 'image' in media.type:
                metadata['image_url'] = media.url
                break
    
    # Альтернативные способы поиска изображения
    if not metadata['image_url'] and hasattr(entry, 'enclosures'):
        for enclosure in entry.enclosures:
            if hasattr(enclosure, 'type') and 'image' in enclosure.type:
                metadata['image_url'] = enclosure.href
                break
    
    return metadata

def calculate_reading_stats(content):
    """Вычисляет статистику чтения."""
    if not content:
        return 0, 0
    
    # Подсчет слов (простая логика)
    words = re.findall(r'\b\w+\b', content.lower())
    word_count = len(words)
    
    # Время чтения (примерно 200 слов в минуту)
    reading_time = max(1, word_count // 200)
    
    return word_count, reading_time

def setup_database():
    """Настраивает соединение с БД и создает таблицы, если их нет."""
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine) 
    Session = sessionmaker(bind=engine)
    return Session()

def parse_and_save_rss_custom(session, urls=None):
    """Перебирает список URL, парсит каждую ленту и сохраняет новые статьи в БД."""
    if urls is None:
        urls = RSS_URLS
    global_new_count = 0
    
    print(f"🛠️ Начинаем парсинг {len(urls)} RSS-лент...")
    
    for url in urls:
        try:
            print(f"🔍 Парсим ленту {url}")
            feed = feedparser.parse(url)
            
            if feed.bozo:
                print(f"   ⚠️ Предупреждение: RSS-лента может содержать ошибки")
                print(f"   📋 Детали ошибки: {feed.bozo_exception}")
            
            # Проверяем, есть ли записи в ленте
            if not hasattr(feed, 'entries') or not feed.entries:
                print(f"   ❌ Лента пуста или не содержит записей")
                continue
            
            new_count = 0
            feed_title = feed.feed.title if hasattr(feed.feed, 'title') else 'Неизвестный источник'
            print(f"   📰 Источник: {feed_title}")
            
            for i, entry in enumerate(feed.entries):
                try:
                    # Проверяем, существует ли статья
                    exists = session.query(Article).filter_by(title=entry.title).first()
                    if exists:
                        continue
                    
                    print(f"   📄 Обрабатываем статью {i+1}/{len(feed.entries)}: {entry.title[:50]}...")
                    
                    # Извлекаем базовую информацию
                    pub_date = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_date = datetime(*entry.published_parsed[:6])
                    
                    # Извлекаем дополнительные метаданные
                    metadata = extract_article_metadata(entry)
                    
                    # Извлекаем полный контент (с ограничением по времени)
                    print(f"      🔍 Извлекаем полный контент...")
                    full_content = extract_full_content(entry.link)
                    
                    # Вычисляем статистику
                    word_count, reading_time = calculate_reading_stats(full_content)
                    
                    # Создаем статью с расширенными данными
                    new_article = Article(
                        title=entry.title,
                        link=entry.link,
                        published=pub_date,
                        summary=entry.summary if hasattr(entry, 'summary') else 'Нет описания',
                        source=feed_title,
                        feed_url=url,
                        content=full_content,
                        author=metadata['author'],
                        category=metadata['category'],
                        image_url=metadata['image_url'],
                        word_count=word_count,
                        reading_time=reading_time,
                        is_processed=True
                    )
                    
                    session.add(new_article)
                    new_count += 1
                    global_new_count += 1
                    
                    print(f"      ✅ Статья добавлена (слов: {word_count}, время чтения: {reading_time} мин)")
                    
                    # Небольшая пауза между запросами
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"      ❌ Ошибка при обработке статьи: {e}")
                    continue
            
            print(f"   - Обработано записей: {len(feed.entries)}, добавлено новых: {new_count}")
            
        except Exception as e:
            print(f"   - 🔧 Пропускаем проблемную ленту и продолжаем...")
            continue

    try:
        session.commit()
        print(f"\n✅ Успешно завершено.")
        print(f"   Всего добавлено новых записей в БД: {global_new_count}")
        return global_new_count
    except Exception as e:
        session.rollback()
        print(f"\n❌ Критическая ошибка при фиксации транзакции: {e}")
        return 0
    finally:
        pass  # Не закрываем session, так как он управляется извне

def parse_and_save_rss():
    """Оригинальная функция для обратной совместимости"""
    session = setup_database()
    try:
        return parse_and_save_rss_custom(session)
    finally:
        session.close()

# --- НОВАЯ ФУНКЦИЯ ДЛЯ ПРОВЕРКИ ---
def check_articles_custom(session, limit=10):
    """Извлекает и выводит последние 'limit' статей из БД."""
    # Запрос всех статей, отсортированных по ID (последние добавленные внизу)
    articles = session.query(Article).order_by(Article.id.desc()).limit(limit).all()
    
    print(f"\n--- Последние {len(articles)} статей из базы данных ---")
    if not articles:
        print("База данных пуста.")
        return []
    
    result = []
    for article in articles:
        article_data = {
            'id': article.id,
            'source': article.source,
            'title': article.title,
            'author': article.author or 'Не указан',
            'category': article.category or 'Не указана',
            'published': article.published.strftime('%Y-%m-%d %H:%M:%S') if article.published else 'Нет данных',
            'created_at': article.created_at.strftime('%Y-%m-%d %H:%M:%S') if article.created_at else 'Нет данных',
            'word_count': article.word_count or 0,
            'reading_time': article.reading_time or 0,
            'is_processed': article.is_processed,
            'link': article.link,
            'image_url': article.image_url,
            'summary': article.summary,
            'content': article.content
        }
        result.append(article_data)
    
    return result

def check_articles(limit=10):
    """Оригинальная функция для обратной совместимости"""
    session = setup_database()
    try:
        return check_articles_custom(session, limit)
    finally:
        session.close()

def get_articles_stats_custom(session):
    """Показывает статистику по статьям в базе данных."""
    
    total_articles = session.query(Article).count()
    processed_articles = session.query(Article).filter(Article.is_processed == True).count()
    
    # Статистика по источникам
    sources = session.query(Article.source, session.query(Article).filter(Article.source == Article.source).count()).group_by(Article.source).all()
    
    # Средняя статистика
    avg_words = session.query(Article.word_count).filter(Article.word_count.isnot(None)).all()
    avg_words = sum([w[0] for w in avg_words]) / len(avg_words) if avg_words else 0
    
    stats = {
        'total_articles': total_articles,
        'processed_articles': processed_articles,
        'avg_words': round(avg_words, 0),
        'sources': [{'source': source, 'count': count} for source, count in sources]
    }
    
    return stats

def get_articles_stats():
    """Оригинальная функция для обратной совместимости"""
    session = setup_database()
    try:
        return get_articles_stats_custom(session)
    finally:
        session.close()


class RSSParser:
    """Класс для парсинга RSS лент и сохранения в базу данных"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or DATABASE_URL
        self.session = None
    
    def connect(self):
        """Подключение к базе данных"""
        engine = create_engine(self.database_url)
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        self.session = Session()
        return self.session
    
    def close(self):
        """Закрытие соединения"""
        if self.session:
            self.session.close()
    
    def parse_and_save(self, urls: list = None):
        """Парсинг и сохранение статей"""
        if not self.session:
            self.connect()
        
        urls = urls or RSS_URLS
        return parse_and_save_rss_custom(self.session, urls)
    
    def get_stats(self):
        """Получение статистики"""
        if not self.session:
            self.connect()
        
        return get_articles_stats_custom(self.session)
    
    def check_articles(self, limit: int = 10):
        """Проверка последних статей"""
        if not self.session:
            self.connect()
        
        return check_articles_custom(self.session, limit)
