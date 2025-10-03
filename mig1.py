import json
import sqlite3
from datetime import datetime
import math

DB_PATH = "rss_articles.db"   # путь к твоей SQLite базе
JSON_PATH = "financial_news.json" # JSON с новостями

# Функция для подсчёта слов и времени чтения
def analyze_text(text: str):
    words = text.split()
    word_count = len(words)
    reading_time = max(1, math.ceil(word_count / 200))  # 200 слов/мин
    return word_count, reading_time

# Загружаем JSON
with open(JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

# Подключаемся к SQLite
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

for post in data:
    title = post.get("text", "")
    link = post.get("url")
    published = datetime.fromisoformat(post.get("date").replace("Z", "+00:00"))
    source = post.get("channel")
    content = post.get("text", "")
    category = ", ".join(post.get("categories", []))
    
    # Считаем статистику
    word_count, reading_time = analyze_text(content)

    # Вставляем данные
    cursor.execute("""
        INSERT OR IGNORE INTO articles 
        (title, link, published, summary, source, feed_url, content, author, category, image_url, word_count, reading_time, is_processed, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (
        title, link, published, None, source, None, content, None, category, None, word_count, reading_time, False
    ))

# Сохраняем изменения
conn.commit()
conn.close()

print("✅ Данные успешно добавлены в SQLite")
