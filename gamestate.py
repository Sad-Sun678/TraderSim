# ================================================
# gamestate.py (PURE GAME LOGIC – NO PYGAME)
# ================================================
import math
import random
import json
import sqlite3


class GameState:
    def __init__(self):
        # --------------------------------------------
        # BASE STRUCTS & LOADING
        # --------------------------------------------
        self.account = {}
        self.portfolio = {}
        self.tickers = {}
        self.global_events = {}
        self.company_events = {}
        # SAFETY FALLBACKS FOR EMPTY / PARTIAL LOADS

        # UI things that DO NOT belong here
        # will be removed in step 2.
        self.selected_stock = None
        self.chart_zoom = 1.0
        self.chart_offset = 0

        # Load data (your load_from_db logic stays)
        self.load_from_db()
        self.account.setdefault("money", 0)
        self.account.setdefault("market_time", 0)
        self.account.setdefault("market_day", 1)
        self.account.setdefault("market_open", 570)
        self.account.setdefault("market_close", 960)

        # Gameplay timing
        self.market_time = self.account.get("market_time", 0)
        self.market_day = self.account.get("market_day", 1)
        self.market_open = self.account.get("market_open", 570)
        self.market_close = self.account.get("market_close", 960)
        self.minutes_per_tick = 1

        # Market systems
        self.sector_sentiment = {}
        self.market_mood = 0
        self.game_season = "normal"
        self.season_profiles = {
            "normal": {"trend_bias": 0.0, "volatility_mult": 1.0, "volume_mult": 1.0}
        }

        # BUY / ORDER FORCE SYSTEM
        self.recently_bought = {}

        # News messages
        self.news_messages = []

    # ==========================================================
    # DATABASE & LOAD FUNCTIONS (UNCHANGED)
    # ==========================================================
    def load_from_db(self):
        # Paste your existing load_from_db body here unchanged.
        pass

    def save_to_db(self):
        # Keep your save logic.
        pass

    # ==========================================================
    # MARKET DAY ADVANCE
    # ==========================================================
    def _advance_game_day(self):
        self.market_day += 1
        # Reset daily structures if needed
        for data in self.tickers.values():
            data["volume"] = max(0, int(data["avg_volume"] * random.uniform(0.5, 1.2)))

    # ==========================================================
    # BUY & SELL
    # ==========================================================
    def buy_stock(self, stock_name, qty=1):
        info = self.tickers[stock_name]
        price = info["current_price"]
        total = price * qty

        if self.account["money"] < total:
            return False

        self.account["money"] -= total
        self.portfolio[stock_name] = self.portfolio.get(stock_name, 0) + qty

        # ORDER FORCE TRACKING
        if stock_name not in self.recently_bought:
            self.recently_bought[stock_name] = {
                "order_force_time_delta": qty
            }
        else:
            self.recently_bought[stock_name]["order_force_time_delta"] += qty

        return True

    def sell_stock(self, stock_name, qty=1):
        if self.portfolio.get(stock_name, 0) < qty:
            return False

        info = self.tickers[stock_name]
        price = info["current_price"]
        total = price * qty

        self.portfolio[stock_name] -= qty
        if self.portfolio[stock_name] <= 0:
            del self.portfolio[stock_name]

        self.account["money"] += total
        return True

    # ==========================================================
    # MARKET TICK (PRICE ENGINE)
    # ==========================================================
    def apply_tick_price(self):
        self.market_time += self.minutes_per_tick

        # rollover to next day
        while self.market_time >= 1440:
            self.market_time -= 1440
            self._advance_game_day()

        self.is_market_open = self.market_open <= self.market_time <= self.market_close

        for stock_name, data in self.tickers.items():
            # --------------------------------------------
            # SETUP
            # --------------------------------------------
            base = data["base_price"]
            prev = data["current_price"]
            last = data["last_price"]
            data["last_price"] = prev

            # ORDER FORCE
            if stock_name in self.recently_bought:
                td = self.recently_bought[stock_name]["order_force_time_delta"]
                td *= 0.98
                self.recently_bought[stock_name]["order_force_time_delta"] = td
                order_force = td * 0.000005
            else:
                order_force = 0.0

            # MEAN REVERSION
            fair_value_force = (base - prev) * (data["gravity"] * 1.3)

            # MOMENTUM
            diff = prev - last
            data["trend"] = data["trend"] * 0.9 + diff * 0.1
            momentum_force = data["trend"] * 0.01

            # VOLATILITY
            vol_cat = data["volatility"]
            vol_map = {
                "low": (0.003, 0.015),
                "medium": (0.015, 0.06),
                "high": (0.04, 0.14),
            }
            sigma_min, sigma_max = vol_map[vol_cat]
            sigma = random.uniform(sigma_min, sigma_max)

            vol_multiplier = max(0.75, min(3.0, data["volume"] / data["avg_volume"]))
            volatility_force = random.gauss(0, sigma) * vol_multiplier

            # SECTOR FORCE
            sector_force = self.sector_sentiment.get(data["sector"], 0) * 0.003

            # NOISE + MOOD
            noise = random.gauss(0, 0.003 if self.is_market_open else 0.0004)
            mood = self.market_mood

            # FINAL CHANGE
            change = (
                fair_value_force
                + momentum_force
                + volatility_force
                + order_force
                + sector_force
                + noise
                + mood
            )

            new_price = max(0.01, prev + change)
            data["current_price"] = round(new_price, 2)

            # CANDLE LOGIC (keep same)
            if "ohlc_buffer" not in data:
                data["ohlc_buffer"] = []

            micro_prices = []
            micro = prev
            for i in range(5):
                micro += random.gauss(0, sigma * 0.4)
                micro = max(0.01, micro)
                micro_prices.append(micro)

            data["ohlc_buffer"].extend(micro_prices)
            data["ohlc_buffer"].append(new_price)

            prices = data["ohlc_buffer"]
            entry = {
                "day": self.market_day,
                "time": int(self.market_time),
                "open": prices[0],
                "high": max(prices),
                "low": min(prices),
                "close": prices[-1],
                "volume": data["volume"],
            }
            data.setdefault("day_history", []).append(entry)
            data["ohlc_buffer"] = []
