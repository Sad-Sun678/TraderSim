import sqlite3

# Path to your DB — update if yours is named differently
DB_PATH = "game.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

print("Dropping old candles table (if exists)...")
cur.execute("DROP TABLE IF EXISTS candles;")

print("Creating clean candles table...")
cur.execute("""
CREATE TABLE candles (
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

conn.commit()
conn.close()

print("✔ Done. candles table reset successfully.")
