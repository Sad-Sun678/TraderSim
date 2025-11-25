import sqlite3

# Create / connect to DB
conn = sqlite3.connect("game.db")
cur = conn.cursor()

# ============================
# MAIN TABLES
# ============================

cur.execute("""
CREATE TABLE IF NOT EXISTS tickers (
    ticker TEXT PRIMARY KEY,
    name TEXT,
    sector TEXT,
    current_price REAL,
    last_price REAL,
    base_price REAL,
    volatility TEXT,
    gravity REAL,
    trend REAL,
    ath REAL,
    atl REAL,
    buy_qty INTEGER,
    volume INTEGER,
    avg_volume INTEGER
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS candles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT,
    day INTEGER,
    time INTEGER,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS portfolio (
    ticker TEXT PRIMARY KEY,
    shares INTEGER,
    bought_at TEXT,       -- JSON string
    sell_qty INTEGER
);
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS account (
    id INTEGER PRIMARY KEY,
    money REAL,
    market_time INTEGER,
    market_open INTEGER,
    market_close INTEGER,
    market_day INTEGER
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT,
    message TEXT,
    color TEXT,
    timestamp INTEGER
);
""")

cur.execute("""
    INSERT OR REPLACE INTO account
    (id, money, market_time, market_open, market_close, market_day)
    VALUES (1, 10000, 0, 570, 960, 1)
""")
print("Database created successfully.")
conn.commit()
conn.close()
