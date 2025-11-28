# candle_manager.py

import sqlite3

class CandleManager:
    MAX_CANDLES = 2000

    def __init__(self, db_path="game.db"):
        self.db_path = db_path

    # ----------------------------------------------------
    # SAVE ALL CANDLES (used inside GameState.autosave)
    # ----------------------------------------------------
    def save_all(self, tickers_obj):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        for name, stock in tickers_obj.items():

            # Trim RAM first
            stock.day_history = stock.day_history[-self.MAX_CANDLES:]

            # Clear old candles for this ticker
            cur.execute("DELETE FROM candles WHERE ticker = ?", (name,))

            # Insert current candle history
            for c in stock.day_history:
                cur.execute("""
                    INSERT INTO candles 
                    (ticker, day, time, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    name,
                    c["day"],
                    c["time"],
                    c["open"],
                    c["high"],
                    c["low"],
                    c["close"],
                    c["volume"]
                ))

        conn.commit()
        conn.close()

    # ----------------------------------------------------
    # LOAD ALL CANDLES (used inside GameState.load_from_db)
    # ----------------------------------------------------
    def load_all(self, tickers_dict):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        rows = cur.execute("""
            SELECT ticker, day, time, open, high, low, close, volume
            FROM candles
            ORDER BY ticker, day, time
        """).fetchall()

        for ticker, day, time, o, h, l, c, vol in rows:
            if ticker in tickers_dict:
                tickers_dict[ticker]["day_history"].append({
                    "day": day,
                    "time": time,
                    "open": o,
                    "high": h,
                    "low": l,
                    "close": c,
                    "volume": vol
                })

        conn.close()

    def add_price(self, stock_dict, day, time, price, volume, base_minutes=5):
        """
        Updates the OHLC candle for the current 5-minute bucket.
        Automatically creates a new candle when needed.

        stock_dict = ticker dict from GameState.tickers[t]
        day, time = current simulation day/time
        price = latest traded price
        volume = traded volume
        """

        candles = stock_dict["day_history"]

        # Determine current candle time bucket (e.g., 10:00, 10:05, 10:10...)
        bucket = (time // base_minutes) * base_minutes

        # If no candles yet OR new bucket → start new candle
        if not candles or candles[-1]["time"] != bucket or candles[-1]["day"] != day:
            candles.append({
                "day": day,
                "time": bucket,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": volume
            })
            return

        # Otherwise update the existing candle
        c = candles[-1]
        c["close"] = price
        c["high"] = max(c["high"], price)
        c["low"] = min(c["low"], price)
        c["volume"] += volume
