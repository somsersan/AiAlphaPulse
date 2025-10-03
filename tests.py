import sqlite3, pathlib

db = pathlib.Path("data/rss_articles.db")
con = sqlite3.connect(db)
cur = con.cursor()

# list tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
print("Tables:", [r[0] for r in cur.fetchall()])

# count rows in the main table (change 'articles' to yours)
cur.execute("SELECT COUNT(*) FROM articles;")
print("Row count:", cur.fetchone()[0])

con.close()