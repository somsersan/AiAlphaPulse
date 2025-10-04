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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("parser")

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

    'MinorityMindset', 'BiggerPockets', 'RyanScribner',
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
