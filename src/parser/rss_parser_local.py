import json
from dataclasses import dataclass, field
from datetime import datetime
import re
import time
from typing import Dict, List, Optional
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base

from .rss_parser import (
    calculate_reading_stats,
    extract_article_metadata,
    extract_full_content,
)


    # # Investopedia (Все статьи)
    # 'https://news.google.com/rss?hl=ru&gl=RU&ceid=RU:ru',
    # 'https://www.investopedia.com/rss-feed-4790074',
RSS_URLS = [
    # ----------------------------------------------------
    # ГЛОБАЛЬНЫЕ ФИНАНСОВЫЕ И БИЗНЕС-ИЗДАНИЯ
    # ----------------------------------------------------
    # 'https://lenta.ru/rss/news',
    # 'https://habr.com/ru/rss/hubs/all/'
    
    # # Bloomberg
    # 'https://feeds.bloomberg.com/markets/news.rss',
    # 'https://feeds.bloomberg.com/business/news.rss',
        
    # # CNBC (Top News)
    # 'https://www.cnbc.com/id/100003114/device/rss/rss.html',
        
        
    # # Business Insider (Top News)
    # 'https://www.businessinsider.com/rss',


    # "https://smart-lab.ru/news/rss/",
    # "https://smart-lab.ru/forum/rss/",
    
    # # ----------------------------------------------------
    # # РОССИЙСКИЕ / РУССКОЯЗЫЧНЫЕ
    # # ----------------------------------------------------
    
    # # РБК (Все новости)
    # 'http://static.feed.rbc.ru/rbc/logical/footer/news.rss',
    
    # # Ведомости (Главные новости)
    # 'https://www.vedomosti.ru/rss/news',
    
    # # Коммерсантъ (Финансы / Рынки)
    # 'https://www.kommersant.ru/RSS/finance.xml',
    
    # Рабочие RSS-ленты
    # 'https://tass.ru/rss/v2.xml',  # ТАСС - работает
    
    # ----------------------------------------------------
    # ЭКОНОМИЧЕСКИЕ RSS-ЛЕНТЫ (ПРОВЕРЕНЫ)
    # ----------------------------------------------------
    # 'https://www.ft.com/?format=rss',  # Financial Times - работает
    # 'https://fortune.com/feed',  # Fortune - работает
    # 'https://www.investing.com/rss/news.rss',  # Investing.com - работает
    # 'https://finance.yahoo.com/news/rssindex',  # Yahoo Finance - работает
    # 'https://financialpost.com/feed',  # Financial Post - работает
    
    # ----------------------------------------------------
    # РОССИЙСКИЕ ЭКОНОМИЧЕСКИЕ RSS-ЛЕНТЫ (ПРОВЕРЕНЫ)
    # ----------------------------------------------------
    # 'https://www.kommersant.ru/RSS/news.xml',  # Коммерсантъ - работает
]

# Имя файла базы данных SQLite
DATABASE_FILE = 'rss_articles2.db'
DATABASE_URL = f"sqlite:///{DATABASE_FILE}"

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

def setup_database():
    """Настраивает соединение с БД и создает таблицы, если их нет."""
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine) 
    Session = sessionmaker(bind=engine)
    return Session()

def parse_and_save_rss():
    """Перебирает список URL, парсит каждую ленту и сохраняет новые статьи в БД."""
    session = setup_database()
    global_new_count = 0
    
    print(f"🛠️ Начинаем парсинг {len(RSS_URLS)} RSS-лент...")
    
    for url in RSS_URLS:
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
                    content_result = extract_full_content(entry.link)
                    full_content = content_result.text

                    # Вычисляем статистику
                    word_count, reading_time = calculate_reading_stats(full_content)

                    content_to_store = full_content
                    if content_result.links:
                        links_block = "\n\nСсылки:\n" + "\n".join(content_result.links)
                        content_to_store = (full_content + links_block) if full_content else links_block

                    # Создаем статью с расширенными данными
                    new_article = Article(
                        title=entry.title,
                        link=entry.link,
                        published=pub_date,
                        summary=entry.summary if hasattr(entry, 'summary') else 'Нет описания',
                        source=feed_title,
                        feed_url=url,
                        content=content_to_store,
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
        print(f"   Файл базы данных: {DATABASE_FILE}")
    except Exception as e:
        session.rollback()
        print(f"\n❌ Критическая ошибка при фиксации транзакции: {e}")
    finally:
        session.close()

# --- НОВАЯ ФУНКЦИЯ ДЛЯ ПРОВЕРКИ ---
def check_articles(limit=10):
    """Извлекает и выводит последние 'limit' статей из БД."""
    session = setup_database()
    # Запрос всех статей, отсортированных по ID (последние добавленные внизу)
    articles = session.query(Article).order_by(Article.id.desc()).limit(limit).all()
    
    print(f"\n--- Последние {len(articles)} статей из базы данных ({DATABASE_FILE}) ---")
    if not articles:
        print("База данных пуста.")
        return
    
    for article in articles:
        print("-" * 60)
        print(f"ID: {article.id}")
        print(f"Источник: {article.source}")
        print(f"Заголовок: {article.title}")
        print(f"Автор: {article.author or 'Не указан'}")
        print(f"Категория: {article.category or 'Не указана'}")
        print(f"Дата публикации: {article.published.strftime('%Y-%m-%d %H:%M:%S') if article.published else 'Нет данных'}")
        print(f"Дата добавления: {article.created_at.strftime('%Y-%m-%d %H:%M:%S') if article.created_at else 'Нет данных'}")
        print(f"Слов: {article.word_count or 0}")
        print(f"Время чтения: {article.reading_time or 0} мин")
        print(f"Обработана: {'Да' if article.is_processed else 'Нет'}")
        print(f"Ссылка: {article.link}")
        if article.image_url:
            print(f"Изображение: {article.image_url}")
        if article.summary:
            print(f"Краткое описание: {article.summary[:200]}{'...' if len(article.summary) > 200 else ''}")
        if article.content:
            print(f"Полный текст: {article.content[:300]}{'...' if len(article.content) > 300 else ''}")
        
    session.close()

def get_articles_stats():
    """Показывает статистику по статьям в базе данных."""
    session = setup_database()
    
    total_articles = session.query(Article).count()
    processed_articles = session.query(Article).filter(Article.is_processed == True).count()
    
    # Статистика по источникам
    sources = session.query(Article.source, session.query(Article).filter(Article.source == Article.source).count()).group_by(Article.source).all()
    
    # Средняя статистика
    avg_words = session.query(Article.word_count).filter(Article.word_count.isnot(None)).all()
    avg_words = sum([w[0] for w in avg_words]) / len(avg_words) if avg_words else 0
    
    print(f"\n--- Статистика базы данных ---")
    print(f"Всего статей: {total_articles}")
    print(f"Обработано: {processed_articles}")
    print(f"Среднее количество слов: {avg_words:.0f}")
    print(f"\nСтатьи по источникам:")
    for source, count in sources:
        print(f"  {source}: {count}")
    
    session.close()

# --- БЛОК ЗАПУСКА ---
if __name__ == "__main__":
    parse_and_save_rss()
    # check_articles(limit=5)  # Выводим последние 5 добавленных статей
    # get_articles_stats()  # Показываем статистику
