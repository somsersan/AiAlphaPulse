import asyncio
import httpx
import re
import json
import csv
import logging
from bs4 import BeautifulSoup
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("parser")

# PostgreSQL настройки
load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://rss_user:rss_password@localhost:5432/rss_db')

# Определение модели БД (SQLAlchemy)
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

CHANNELS = [
    'RBCNews', 'vedomosti', 'kommersant', 'tass_agency', 'interfaxonline',
    'bitkogan', 'rbc_quote', 'banksta', 'cbonds', 'investfuture',
    'bezposhady', 'bloomeconomy', 'bloombusiness', 'economistg', 'BizLike',
    'finance_pro_tg', 'banki_economy', 'prbezposhady',
    'ru_holder', 'centralbank_russia', 'AlfaBank', 'multievan', 'bankvtb',
    'ozon_bank_official', 'auantonov', 'prostoecon', 'sberbank', 'cb_economics',
    'MarketOverview', 'frank_media', 'lemonfortea', 'div_invest', 'moneyhack',
    'finside', 'platformaonline', 'sf_education', 'intrinsic_value', 'finamalert',
    'SmartLab', 'tradernet', 'finam_trade', 'rutrade',

    'Bloomberg', 'Investingcom', 'TheEconomist', 'moneycontrolcom',
    'MarketAlert', 'Stocktwits', 'FinvizAlerts', 'CryptoMarkets', 'cbrstocks',
    'beststocks_usadividends', 'if_stocks', 'realvisiontv',
    'spydell_finance', 'WallStreetBets', 'SatoshiCalls', 'Hypercharts',

    'BiggerPockets', 'RyanScribner',
    'JeffRose', 'MarkoWhiteBoardFinance',
    'DevinCarroll', 'BenHedges'
]

KEYWORDS = {
    "акцизы": r"(акциз|табак|алкоголь|топливо|бензин|сигарет)",
    "акции": r"(акци|бирж|торг|котировк|индекс|мосбирж|ммвб|ipo|дивиденд)",
    "мировая экономика": r"(доллар|евро|курс|нефть|золото|экспорт|импорт|санкци|опек|фрс|fed)",
}

BASE_URL = "https://t.me/s/"

@dataclass
class Post:
    channel: str
    post_id: str
    date: str
    text: str
    categories: List[str]
    views: str
    url: str

class TelegramParser:
    def __init__(self):
        self.client = httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            follow_redirects=False
        )

    async def fetch_channel(self, channel: str, limit: int = 30) -> List[Post]:
        url = f"{BASE_URL}{channel}"
        posts: List[Post] = []

        try:
            resp = await self.client.get(url, timeout=15)
            if resp.status_code == 302:
                log.warning(f"Пропускаем @{channel} → редирект")
                return []

            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            messages = soup.find_all("div", class_="tgme_widget_message", limit=limit)

            for msg in messages:
                post = self.parse_message(msg, channel)
                if post:
                    posts.append(post)

            log.info(f"✓ @{channel}: {len(posts)} постов")
        except Exception as e:
            log.error(f"✗ Ошибка @{channel}: {e}")

        return posts

    def parse_message(self, msg, channel: str) -> Post | None:
        try:
            text_div = msg.find("div", class_="tgme_widget_message_text")
            text = text_div.get_text(strip=True) if text_div else ""
            if len(text) < 10:
                return None

            time_elem = msg.find("time")
            date_str = time_elem["datetime"] if time_elem and time_elem.has_attr("datetime") else datetime.now().isoformat()

            link = msg.get("data-post", "")
            post_id = link.split("/")[-1] if link else "unknown"

            views_elem = msg.find("span", class_="tgme_widget_message_views")
            views = views_elem.get_text(strip=True) if views_elem else "0"

            categories = self.categorize(text)


            return Post(
                channel=f"@{channel}",
                post_id=post_id,
                date=date_str,
                text=text.strip(),
                categories=categories,
                views=views,
                url=f"https://t.me/{channel}/{post_id}"
            )
        except Exception as e:
            log.warning(f"Ошибка парсинга поста @{channel}: {e}")
            return None

    def categorize(self, text: str) -> List[str]:
        text_lower = text.lower()
        categories = [cat for cat, pattern in KEYWORDS.items() if re.search(pattern, text_lower)]
        categories.append("все новости")
        return categories

    async def parse_all(self, channels: List[str], limit: int = 30) -> List[Post]:
        tasks = [self.fetch_channel(ch, limit) for ch in channels]
        results = await asyncio.gather(*tasks)
        return [p for channel_posts in results for p in channel_posts]

    async def close(self):
        await self.client.aclose()

def save_json(posts: List[Post], filename="financial_news.json"):
    data = []
    for i, p in enumerate(posts, start=1):
        article = {
            "id": i,
            "title": p.text[:255],
            "link": p.url,
            "published": p.date,
            "summary": p.text[:500],
            "source": p.channel,
            "feed_url": f"https://t.me/{p.channel[1:]}",
            "content": p.text,
            "author": None,
            "category": ", ".join(p.categories),
            "image_url": None,
            "word_count": len(p.text.split()),
            "reading_time": max(1, len(p.text.split()) // 200),
            "is_processed": False,
            "created_at": datetime.now().isoformat()
        }
        data.append(article)

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log.info(f"JSON сохранён: {filename}")

def save_csv(posts: List[Post], filename="financial_news.csv"):
    if not posts:
        return
    with open(filename, "w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "id","title","link","published","summary","source","feed_url","content",
            "author","category","image_url","word_count","reading_time","is_processed","created_at"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for i, p in enumerate(posts, start=1):
            writer.writerow({
                "id": i,
                "title": p.text[:255],
                "link": p.url,
                "published": p.date,
                "summary": p.text[:500],
                "source": p.channel,
                "feed_url": f"https://t.me/{p.channel[1:]}",
                "content": p.text,
                "author": None,
                "category": ", ".join(p.categories),
                "image_url": None,
                "word_count": len(p.text.split()),
                "reading_time": max(1, len(p.text.split()) // 200),
                "is_processed": False,
                "created_at": datetime.now().isoformat()
            })
    log.info(f"CSV сохранён: {filename}")

def print_stats(posts: List[Post]):
    log.info(f"Всего постов: {len(posts)}")
    cats: Dict[str, int] = {}
    chans: Dict[str, int] = {}
    for p in posts:
        for c in p.categories:
            cats[c] = cats.get(c, 0) + 1
        chans[p.channel] = chans.get(p.channel, 0) + 1

    print("\n📑 По категориям:")
    for c, n in sorted(cats.items(), key=lambda x: x[1], reverse=True):
        print(f"  {c}: {n}")

    print("\n📺 По каналам:")
    for c, n in sorted(chans.items(), key=lambda x: x[1], reverse=True):
        print(f"  {c}: {n}")

def setup_database():
    """Настраивает соединение с БД и создает таблицы, если их нет."""
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine) 
    Session = sessionmaker(bind=engine)
    return Session()

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

async def parse_and_save_telegram():
    """Парсит Telegram каналы и сохраняет новые посты в БД."""
    session = setup_database()
    global_new_count = 0
    
    log.info(f"🛠️ Начинаем парсинг {len(CHANNELS)} Telegram каналов...")
    
    parser = TelegramParser()
    try:
        posts = await parser.parse_all(CHANNELS, limit=20)
        
        for post in posts:
            try:
                # Проверяем, существует ли статья
                exists = session.query(Article).filter_by(title=post.text[:255]).first()
                if exists:
                    continue
                
                log.info(f"📄 Обрабатываем пост: {post.text[:50]}...")
                
                # Парсим дату
                pub_date = None
                try:
                    pub_date = datetime.fromisoformat(post.date.replace('Z', '+00:00'))
                except:
                    pub_date = datetime.now()
                
                # Вычисляем статистику
                word_count, reading_time = calculate_reading_stats(post.text)
                
                # Создаем статью
                new_article = Article(
                    title=post.text[:255],  # Ограничиваем длину заголовка
                    link=post.url,
                    published=pub_date,
                    summary=post.text[:500],  # Первые 500 символов как summary
                    source=post.channel,
                    feed_url=f"https://t.me/{post.channel[1:]}",  # Убираем @
                    content=post.text,
                    author=None,  # В Telegram постах обычно нет автора
                    category=", ".join(post.categories),
                    image_url=None,  # Пока не извлекаем изображения
                    word_count=word_count,
                    reading_time=reading_time,
                    is_processed=True
                )
                
                session.add(new_article)
                global_new_count += 1
                
                log.info(f"✅ Пост добавлен (слов: {word_count}, время чтения: {reading_time} мин)")
                
            except Exception as e:
                log.error(f"❌ Ошибка при обработке поста: {e}")
                continue
        
        session.commit()
        log.info(f"✅ Telegram парсинг завершен. Добавлено новых записей: {global_new_count}")
        return global_new_count
        
    except Exception as e:
        session.rollback()
        log.error(f"❌ Критическая ошибка при парсинге Telegram: {e}")
        return 0
    finally:
        session.close()
        await parser.close()

async def main():
    log.info(" Старт парсинга...")
    parser = TelegramParser()
    posts = await parser.parse_all(CHANNELS, limit=20)
    await parser.close()

    if not posts:
        log.error("Посты не собраны")
        return

    print_stats(posts)
    save_json(posts)
    save_csv(posts)
