import sqlite3
import json

DB_PATH = "trader.db"

# -----------------------------------
# INTERNAL: get a connection per call
# -----------------------------------
def get_conn():
    return sqlite3.connect(DB_PATH)


# ======================================================
# TICKER TABLE: insert/update one ticker
# ======================================================
def save_ticker(symbol, data):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO tickers (
            symbol, name, sector, base_price, volatility, gravity,
            current_price, last_price, trend, ath, atl,
            avg_volume, volume, volume_cap, last_breakout_time,
            recent_prices
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(symbol) DO UPDATE SET
            name = excluded.name,
            sector = excluded.sector,
            base_price = excluded.base_price,
            volatility = excluded.volatility,
            gravity = excluded.gravity,
            current_price = excluded.current_price,
            last_price = excluded.last_price,
            trend = excluded.trend,
            ath = excluded.ath,
            atl = excluded.atl,
            avg_volume = excluded.avg_volume,
            volume = excluded.volume,
            volume_cap = excluded.volume_cap,
            last_breakout_time = excluded.last_breakout_time,
            recent_prices = excluded.recent_prices;
    """, (
        symbol,
        data["name"],
        data["sector"],
        data["base_price"],
        data["volatility"],
        data["gravity"],
        data["current_price"],
        data["last_price"],
        data["trend"],
        data["ath"],
        data["atl"],
        data["avg_volume"],
        data["volume"],
        data["volume_cap"],
        data["last_breakout_time"],
        json.dumps(data.get("recent_prices", [])),
    ))

    conn.commit()
    conn.close()


# ======================================================
# CANDLES TABLE: append OHLC candle
# ======================================================
def insert_candle(symbol, candle):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO candles (symbol, day, time, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        symbol,
        candle["day"],
        candle["time"],
        candle["open"],
        candle["high"],
        candle["low"],
        candle["close"],
        candle["volume"],
    ))

    conn.commit()
    conn.close()


# ======================================================
# PORTFOLIO TABLE: update 1 stock
# ======================================================
def save_portfolio_row(symbol, row):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO portfolio (symbol, shares, bought_at)
        VALUES (?, ?, ?)
        ON CONFLICT(symbol) DO UPDATE SET
            shares = excluded.shares,
            bought_at = excluded.bought_at;
    """, (
        symbol,
        row["shares"],
        json.dumps(row["bought_at"]),
    ))

    conn.commit()
    conn.close()


# ======================================================
# ACCOUNT TABLE
# ======================================================
def save_account(data):
    conn = get_conn()
    cur = conn.cursor()

    # Remove previous row (only 1 row exists)
    cur.execute("DELETE FROM account")

    cur.execute("""
        INSERT INTO account (money, market_time, market_open, market_close, market_day)
        VALUES (?, ?, ?, ?, ?)
    """, (
        data["money"],
        data["market_time"],
        data["market_open"],
        data["market_close"],
        data["market_day"]
    ))

    conn.commit()
    conn.close()


# ======================================================
# NEWS TABLE
# ======================================================
def insert_news(symbol, text, color, timestamp):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO news (symbol, message, color, timestamp)
        VALUES (?, ?, ?, ?)
    """, (symbol, text, json.dumps(color), timestamp))

    conn.commit()
    conn.close()
