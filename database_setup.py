import sqlite3

# Create / connect to DB
conn = sqlite3.connect("trader.db")
cur = conn.cursor()

# ============================
# MAIN TABLES
# ============================

cur.execute("""
CREATE TABLE IF NOT EXISTS tickers (
    symbol TEXT PRIMARY KEY,
    name TEXT,
    sector TEXT,
    base_price REAL,
    volatility TEXT,
    gravity REAL,
    current_price REAL,
    last_price REAL,
    trend REAL,
    ath REAL,
    atl REAL,
    avg_volume INTEGER,
    volume INTEGER,
    volume_cap REAL,
    last_breakout_time INTEGER,
    recent_prices TEXT
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS candles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT,
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
    symbol TEXT,
    shares INTEGER,
    bought_at TEXT
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS account (
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

print("Database created successfully.")
conn.commit()
conn.close()
