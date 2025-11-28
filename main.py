import sys

import file_functions as ff
import random
import pygame
import time
import gui
import math
import numpy
import sqlite3
import json
DB_PATH = "game.db"


from gui import apply_cached_pixelation

def db_connect():
    return sqlite3.connect(DB_PATH)


class GameState:
    def __init__(self):
        # =====================================================
        # 1. BASE STRUCTS – overwritten by load_from_db()
        # =====================================================
        self.account = {
            "money": 0,
            "market_time": 0,
            "market_open": 570,
            "market_close": 960,
            "market_day": 1
        }
        self.portfolio = {}
        self.tickers = {}
        self.recently_bought = {}

        # =====================================================
        # 2. LOAD EVERYTHING FROM SQLITE
        # =====================================================
        self.load_from_db()

        # sync base state
        self.game_day = self.account["market_day"]
        self.market_time = self.account["market_time"]
        self.market_open = self.account["market_open"]
        self.market_close = self.account["market_close"]

        # =====================================================
        # 3. ENSURE RUNTIME-ONLY FIELDS EXIST
        # =====================================================
        for name, data in self.tickers.items():
            data.setdefault("day_history", [])
            data.setdefault("ohlc_buffer", [])
            data.setdefault("recent_prices", [])
            data.setdefault("volume_history", [])
            data.setdefault("history", [])
            data.setdefault("last_breakout_time", -9999)
            data.setdefault("volume_cap", data["avg_volume"] * 12)
        for stock_name, stock_data in self.tickers.items():
            self.recently_bought[stock_name] = {
                "order_force_time_delta": 0
            }

        # =====================================================
        # 4. UI & GAME STATE FLAGS
        # =====================================================
        self.global_events = ff.get_json("game", "global_events")
        self.company_events = ff.get_json("game", "company_events")
        self.news_messages = []

        self.selected_stock = None

        # ---- UI Buttons ----
        self.buy_button_rect = None
        self.sell_button_rect = None
        self.add_button_sell_rect = None
        self.minus_button_sell_rect = None
        self.add_button_buy_rect = None
        self.minus_button_buy_rect = None
        self.max_button_buy_rect = None
        self.max_button_sell_rect = None
        self.buy_button_pressed = False
        self.minus_buy_pressed = False
        self.plus_buy_pressed = False
        self.max_buy_pressed = False

        self.minus_sell_pressed = False
        self.plus_sell_pressed = False
        self.max_sell_pressed = False

        self.button_cooldowns = {
            "buy": 0,
            "plus_buy": 0,
            "minus_buy": 0,
            "max_buy": 0,
            "sell": 0,
            "plus_sell": 0,
            "minus_sell": 0,
            "max_sell": 0
        }
        # ---- Screens ----
        self.show_portfolio_screen = False
        self.show_volume = False
        self.show_candles = False
        self.show_visualize_screen = False

        self.toggle_volume_rect = None
        self.toggle_candles_rect = None

        # ---- UI Collections ----
        self.portfolio_click_zones = {}
        self.portfolio_ui = {}
        self.visualize_ui = {}

        # ---- Portfolio Value ----
        self.portfolio_value = self.get_portfolio_value()

        # ---- Pie Slice Animation ----
        self.slice_animating = False
        self.slice_anim_stock = None
        self.slice_anim_timer = 0

        # =====================================================
        # 5. CHART INTERACTION SYSTEM
        # =====================================================
        self.chart_zoom = 1
        self.chart_offset = 0
        self.chart_dragging = False
        self.chart_drag_start_x = 0
        self.chart_offset_start = 0
        self.chart_pixels_per_index = 1
        self.slider_pos = 100

        # =====================================================
        # 6. GAME CLOCK & MARKET SYSTEM
        # =====================================================
        self.game_season = 1
        self.day_in_season = 1
        self.days_per_season = 10
        self.total_seasons = 4
        self.total_days_in_year = self.days_per_season * self.total_seasons

        self.tick_interval = 2
        self.tick_timer = 0

        self.minutes_per_tick = 5

        self.is_market_open = False
        self.market_events = []
        self.trend_decay_rate = 0.1

        # =====================================================
        # 7. VOLATILITY & SEASONAL MODELS
        # =====================================================
        self.volatility_ranges = {
            "low":    (0.002, 0.012),
            "medium": (0.01,  0.05),
            "high":   (0.03,  0.12)
        }

        self.season_profiles = {
            1: {"trend_bias":  0.001,  "volatility_mult": 1.1, "volume_mult": 1.1},
            2: {"trend_bias":  0.0,    "volatility_mult": 1.0, "volume_mult": 1.0},
            3: {"trend_bias": -0.0015, "volatility_mult": 1.4, "volume_mult": 1.2},
            4: {"trend_bias": -0.0005, "volatility_mult": 1.2, "volume_mult": 1.0},
        }

        # =====================================================
        # 8. SECTOR SENTIMENT SYSTEM
        # =====================================================
        self.sector_sentiment = {}
        for ticker, data in self.tickers.items():
            self.sector_sentiment[data["sector"]] = 0.0

        self.market_mood = 0.0


    def apply_tick_price(self):
        self.market_time += self.minutes_per_tick

        # rollover day at midnight
        while self.market_time >= 1440:
            self.market_time -= 1440
            self._advance_game_day()

        self.is_market_open = self.market_open <= self.market_time <= self.market_close
        
        for stock_name, stock_information in self.tickers.items():
            breakout_force = 0.0

            # --------------------------------------------
            # INIT
            # --------------------------------------------
            base = stock_information["base_price"]
            vol_cat = stock_information["volatility"]
            gravity = stock_information["gravity"]
            trend = stock_information["trend"]
            previous_price = stock_information["last_price"]
            current_price = stock_information["current_price"]
            stock_information["last_price"] = current_price
            company_name = stock_information["name"]
            order_force_time_delta = self.recently_bought[stock_name]["order_force_time_delta"]
            order_force = order_force_time_delta

            # --------------------------------------------
            # UPDATE ATH / ATL
            # --------------------------------------------
            if stock_information["history"]:
                hist_max = max(stock_information["history"])
                hist_min = min(stock_information["history"])
                stock_information["ath"] = max(stock_information["ath"], hist_max)
                stock_information["atl"] = min(stock_information["atl"], hist_min)

            # --------------------------------------------
            # 1. MEAN REVERSION
            # --------------------------------------------
            fair_value_force = (base - current_price) * (gravity * 1.3)

            # --------------------------------------------
            # 2. MOMENTUM
            # --------------------------------------------
            price_diff = current_price - previous_price
            stock_information["trend"] = stock_information["trend"] * 0.9 + price_diff * 0.1
            momentum_force = stock_information["trend"] * 0.01

            # --------------------------------------------
            # 3. VOLATILITY REGIME
            # --------------------------------------------
            vol_map = {
                "low": (0.003, 0.015),
                "medium": (0.015, 0.06),
                "high": (0.04, 0.14)
            }

            # MULTIPLIER FIRST
            vol_multiplier = max(0.75, min(3.0, stock_information["volume"] / stock_information["avg_volume"]))

            sigma_min, sigma_max = vol_map[vol_cat]
            sigma = random.uniform(sigma_min, sigma_max)

            volatility_force = random.gauss(0, sigma) * vol_multiplier

            # --------------------------------------------
            # 4. ORDER PRESSURE (balanced + realistic)
            # --------------------------------------------

            # 1) GET AND DECAY BUY PRESSURE FIRST
            order_force_time_delta = self.recently_bought[stock_name]["order_force_time_delta"]
            order_force_time_delta *= 0.98  # exponential decay each tick
            self.recently_bought[stock_name]["order_force_time_delta"] = order_force_time_delta

            # 2) LIQUIDITY FACTOR (whales only move low-volume stocks)
            avg_volume = stock_information["avg_volume"]
            liquidity_factor = 1 / max(1.0, math.sqrt(avg_volume))

            # 3) FINAL ORDER PRESSURE VALUE
            order_force = order_force_time_delta * 0.000001 * liquidity_factor


            # --------------------------------------------
            # 5. SECTOR SENTIMENT
            # --------------------------------------------
            sector_force = self.sector_sentiment.get(stock_information["sector"], 0) * 0.003

            # --------------------------------------------
            # 6. VOLUME SIMULATION
            # --------------------------------------------
            base_vol = stock_information["avg_volume"]
            vol = stock_information["volume"]
            market_time = self.market_time

            if self.is_market_open:

                vol += (base_vol - vol) * 0.05
                vol += random.randint(-int(base_vol * 0.025), int(base_vol * 0.025))

                if "intraday_bias" not in stock_information:
                    stock_information["intraday_bias"] = random.uniform(0.7, 1.3)
                vol *= stock_information["intraday_bias"]

                if "daily_volume_phase" not in stock_information or self.market_time < 5:
                    stock_information["daily_volume_phase"] = random.uniform(-0.7, 0.7)

                phase = stock_information["daily_volume_phase"]
                time_ratio = (market_time - self.market_open) / max(1, self.market_close - self.market_open)
                sin_wave = 1.0 + 0.25 * math.sin(6.28 * (time_ratio + phase))
                vol *= sin_wave

                if 570 <= market_time <= 615:
                    vol *= random.uniform(1.2, 2.0)
                elif 720 <= market_time <= 810:
                    vol *= random.uniform(0.7, 0.95)
                elif 900 <= market_time <= 960:
                    vol *= random.uniform(1.1, 1.7)

                if random.random() < 0.02:
                    vol *= random.uniform(1.3, 3.2)

            else:
                target_ah = base_vol * random.uniform(0.08, 0.18)
                vol += (target_ah - vol) * 0.15
                vol += random.randint(-int(base_vol * 0.005), int(base_vol * 0.005))

            # --------------------------------------------
            # 7. SEASONAL EFFECTS
            # --------------------------------------------
            season = self.game_season
            profile = self.season_profiles[season]
            season_trend_force = profile["trend_bias"]

            volatility_force *= profile["volatility_mult"]
            vol *= profile["volume_mult"]

            # --------------------------------------------
            # 8. VOLUME CAP
            # --------------------------------------------
            if self.is_market_open:
                if vol > stock_information["volume_cap"] * 0.7:
                    stock_information["volume_cap"] *= random.uniform(1.01, 1.05)
                elif vol < stock_information["volume_cap"] * 0.3:
                    stock_information["volume_cap"] *= random.uniform(0.97, 0.995)
                stock_information["volume_cap"] *= random.uniform(0.999, 1.001)

            stock_information["volume_cap"] = max(base_vol * 5, min(stock_information["volume_cap"], base_vol * 40))
            vol = max(150, min(vol, stock_information["volume_cap"]))
            stock_information["volume"] = int(vol)

            stock_information["volume_history"].append(vol)
            if len(stock_information["volume_history"]) > 700:
                stock_information["volume_history"].pop(0)

            # --------------------------------------------
            # 9. MARKET NOISE + MOOD
            # --------------------------------------------
            noise_force = random.gauss(0, 0.003 if self.is_market_open else 0.0004)

            if random.random() < 0.002:
                self.market_mood = random.uniform(-0.003, 0.002)
            mood_force = self.market_mood

            # --------------------------------------------
            # FINAL PRICE
            # --------------------------------------------
            change = (
                    fair_value_force +
                    momentum_force +
                    volatility_force +
                    order_force +
                    sector_force +
                    noise_force +
                    season_trend_force
            )


            new_price = max(0.01, current_price + change)
            stock_information["current_price"] = round(new_price, 2)

            # --------------------------------------------
            # 9. BREAKOUT DETECTION + NEWS
            # --------------------------------------------
            last_close = current_price
            recent_prices = stock_information.get("recent_prices", [])

            cooldown = 120
            t_now = self.market_time

            if t_now - stock_information.get("last_breakout_time", -9999) >= cooldown:

                if len(recent_prices) >= 20:

                    window = recent_prices[-30:]
                    recent_high = max(window)
                    recent_low = min(window)

                    breakout_up = last_close > recent_high * 1.01
                    breakout_down = last_close < recent_low * 0.99

                    if breakout_up:
                        breakout_force = last_close * 0.004
                        volatility_force *= 1.5
                        stock_information["trend"] += last_close * 0.002
                        stock_information["last_breakout_time"] = t_now

                        self.news_messages.append({
                            "text": f"{stock_name} breaks resistance! Bullish breakout!",
                            "color": (0, 255, 0)
                        })


                    elif breakout_down:
                        breakout_force = -last_close * 0.004
                        volatility_force *= 1.6
                        stock_information["trend"] -= last_close * 0.002
                        stock_information["last_breakout_time"] = t_now
                        self.news_messages.append({
                            "text": f"{stock_name} breaks support! Bearish breakdown!",
                            "color": (255, 80, 80)
                        })


                    change += breakout_force

            # push history ONCE (fixed)
            recent_prices.append(last_close)
            recent_prices = recent_prices[-200:]
            stock_information["recent_prices"] = recent_prices

            # --------------------------------------------
            # BUILD 5-MINUTE OHLC CANDLES (WITH MICRO-TICKS)
            # --------------------------------------------

            # Simulate 5 internal 1-minute price movements
            micro_prices = []
            micro_price = current_price
            for i in range(5):
                # small internal movement inside the candle
                micro_change = random.gauss(0, sigma * 0.4)
                micro_price = max(0.01, micro_price + micro_change)
                micro_prices.append(micro_price)

            # Add the micro-moves into the buffer
            stock_information["ohlc_buffer"].extend(micro_prices)

            # Add the final 5-minute closing price
            stock_information["ohlc_buffer"].append(new_price)

            prices = stock_information["ohlc_buffer"]

            # Build proper OHLC candle
            entry = {
                "day": self.game_day,
                "time": int(self.market_time),  # 5,10,15,20...
                "open": prices[0],
                "high": max(prices),
                "low": min(prices),
                "close": prices[-1],
                "volume": stock_information["volume"]
            }

            stock_information["day_history"].append(entry)

            # Reset buffer for next 5-minute candle
            stock_information["ohlc_buffer"] = []

            # Trim in-memory history
            MAX_CANDLES = 2000
            if len(stock_information["day_history"]) > MAX_CANDLES:
                stock_information["day_history"].pop(0)

    def _advance_game_day(self):
        # Move to next day
        self.game_day += 1
        self.day_in_season += 1

        # Season rollover
        if self.day_in_season > self.days_per_season:
            self.game_season += 1
            self.day_in_season = 1

        # Year rollover
        if self.game_season > self.total_seasons:
            self.game_season = 1
            self.game_day = 1
    def get_portfolio_value(self):
        portfolio_value = 0
        for stock in self.portfolio:
            shares = self.portfolio[stock]["shares"]
            price = self.tickers[stock]["current_price"]
            held_total = price * shares
            portfolio_value += held_total
        return portfolio_value


    def buy_stock(self, stock_name, amount_purchased=1):
        data = self.tickers[stock_name]
        price = data["current_price"]
        if self.account["money"] >= price * amount_purchased:
            #subtract total price from players money in account
            self.account["money"] -= price * amount_purchased
            # if not exists add log to recently_bought dict
            if stock_name not in self.recently_bought:
                self.recently_bought[stock_name] = {
                    "order_force_time_delta":amount_purchased
                }
 
            # if not exists add log to self.portfolio
            if stock_name not in self.portfolio:
                self.portfolio[stock_name] = {
                    "shares": 0,
                    "bought_at": []
                }
            # add shares to players portfolio
            self.portfolio[stock_name]["shares"] += amount_purchased
            # add the amount purchased by the player to the order force td
            self.recently_bought[stock_name]["order_force_time_delta"] += amount_purchased
            
            for _ in range(amount_purchased):
                # used for calculating the rolling average buy price
                self.portfolio[stock_name]["bought_at"].append(price)
            print(f"Bought {amount_purchased} share(s) of {stock_name} at {price:.2f} at TIMESTAMP:{self.market_time}")
        else:
            print("Not enough money!")

    def sell_stock(self, stock_name, amount=1):
        if stock_name not in self.portfolio or self.portfolio[stock_name]["shares"] < amount:
            print("Not enough shares to sell!")
            return

        data = self.tickers[stock_name]
        price = data["current_price"]

        self.portfolio[stock_name]["shares"] -= amount
        self.account["money"] += price * amount
        self.portfolio[stock_name]["bought_at"].pop()
        print(f"Sold {amount} share(s) of {stock_name} at ${price:.2f}")


    def handle_buy(self):
        try:
            print("button clicked")
            selected_stock = self.selected_stock
            self.buy_stock(selected_stock,self.tickers[selected_stock]["buy_qty"])
            print("handler passing to buy function")
        except NameError:
            print("Name Error")
            pass

    def handle_sell(self):
        self.sell_stock(self.selected_stock, self.portfolio[self.selected_stock]['sell_qty'])

    def market_is_open(self):
        return self.market_open <= self.market_time <= self.market_close

    def save_candles_to_db(self):

        conn = sqlite3.connect("game.db")
        cur = conn.cursor()
        MAX_CANDLES = 2000

        for name, data in self.tickers.items():

            # Trim RAM
            data["day_history"] = data["day_history"][-MAX_CANDLES:]

            # DELETE ONCE — this is the important fix
            cur.execute("DELETE FROM candles WHERE ticker = ?", (name,))

            # Insert trimmed history
            for c in data["day_history"]:
                cur.execute("""
                            INSERT INTO candles (ticker, day, time, open, high, low, close, volume)
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

    def load_from_db(self):
        '''
        grabs data from game.db and assigns it to self.portfolio, self.account and self.tickers
        '''

        conn = sqlite3.connect("game.db")
        cur = conn.cursor()

        # -----------------------
        # ACCOUNT
        # -----------------------
        row = cur.execute("""
                          SELECT money, market_time, market_open, market_close, market_day
                          FROM account
                          WHERE id = 1
                          """).fetchone()

        if row:
            self.account["money"] = row[0]
            self.account["market_time"] = row[1]
            self.account["market_open"] = row[2]
            self.account["market_close"] = row[3]
            self.account["market_day"] = row[4]
            self.game_day = row[4]

        # -----------------------
        # TICKERS
        # -----------------------
        rows = cur.execute("""
                           SELECT ticker,
                                  name,
                                  sector,
                                  current_price,
                                  last_price,
                                  base_price,
                                  volatility,
                                  gravity,
                                  trend,
                                  ath,
                                  atl,
                                  buy_qty,
                                  volume,
                                  avg_volume
                           FROM tickers
                           """).fetchall()

        self.tickers = {}  # overwrite JSON version

        for row in rows:
            t = row[0]
            self.tickers[t] = {
                "ticker": row[0],
                "name": row[1],
                "sector": row[2],
                "current_price": row[3],
                "last_price": row[4],
                "base_price": row[5],
                "volatility": row[6],
                "gravity": row[7],
                "trend": row[8],
                "ath": row[9],
                "atl": row[10],
                "buy_qty": row[11],
                "volume": row[12],
                "avg_volume": row[13],

                # ALWAYS EMPTY AT LOAD
                "history": [],
                "volume_history": [],
                "recent_prices": [],
                "day_history": [],
                "ohlc_buffer": [],
                "last_breakout_time": -9999
            }

        # -----------------------
        # PORTFOLIO
        # -----------------------
        rows = cur.execute("SELECT ticker, shares, bought_at, sell_qty FROM portfolio").fetchall()

        for t, shares, bought_at, sell_qty in rows:
            self.portfolio[t] = {
                "shares": shares,
                "bought_at": json.loads(bought_at),
                "sell_qty": sell_qty
            }

        # -----------------------
        # CANDLES (OHLC) — persistent chart history
        # -----------------------
        rows = cur.execute("""
                           SELECT ticker, day, time, open, high, low, close, volume
                           FROM candles
                           ORDER BY ticker, day, time
                           """).fetchall()

        for ticker, day, time, o, h, l, c, vol in rows:
            if ticker in self.tickers:
                self.tickers[ticker]["day_history"].append({
                    "day": day,
                    "time": time,
                    "open": o,
                    "high": h,
                    "low": l,
                    "close": c,
                    "volume": vol
                })

        conn.close()

    def autosave(self):
        ''' Writes back self.account, self.portfolio,self.tickers to db and calls the save candles to db function'''
        # Sync account dict with current state
        self.account["market_time"] = self.market_time
        self.account["market_open"] = self.market_open
        self.account["market_close"] = self.market_close
        self.account["market_day"] = self.game_day

        conn = sqlite3.connect("game.db")
        cur = conn.cursor()

        # -------------------------
        # 1. SAVE ACCOUNT
        # -------------------------
        cur.execute("""
                    UPDATE account
                    SET money=?,
                        market_time=?,
                        market_open=?,
                        market_close=?,
                        market_day=?
                    WHERE id = 1
                    """, (
                        self.account["money"],
                        self.account["market_time"],
                        self.account["market_open"],
                        self.account["market_close"],
                        self.account["market_day"]
                    ))

        # -------------------------
        # 2. SAVE PORTFOLIO
        # -------------------------
        for ticker, info in self.portfolio.items():
            cur.execute("""
                        UPDATE portfolio
                        SET shares=?,
                            bought_at=?,
                            sell_qty=?
                        WHERE ticker = ?
                        """, (
                            info["shares"],
                            json.dumps(info["bought_at"]),
                            info["sell_qty"],
                            ticker
                        ))

        # -------------------------
        # 3. SAVE TICKERS
        # -------------------------
        for name, data in self.tickers.items():
            cur.execute("""
                        UPDATE tickers
                        SET current_price=?,
                            last_price=?,
                            base_price=?,
                            volatility=?,
                            gravity=?,
                            trend=?,
                            ath=?,
                            atl=?,
                            buy_qty=?,
                            volume=?,
                            avg_volume=?
                        WHERE ticker = ?
                        """, (
                            data["current_price"],
                            data["last_price"],
                            data["base_price"],
                            data["volatility"],
                            data["gravity"],
                            data["trend"],
                            data["ath"],
                            data["atl"],
                            data["buy_qty"],
                            data["volume"],
                            data["avg_volume"],
                            name
                        ))

        conn.commit()
        conn.close()

        # -------------------------
        # 4. SAVE CANDLES
        # -------------------------
        self.save_candles_to_db()


        # -------------------------
        # 6. TINY JSON BACKUP
        # -------------------------
        # ff.write_json("game", "tickers", self.tickers)
        # ff.write_json("player", "account", self.account)
        # ff.write_json("player", "portfolio", self.portfolio)

    def simulate_days(self, days_to_simulate):
        ticks_per_day = (self.market_close - self.market_open) // self.minutes_per_tick

        for _ in range(days_to_simulate):
            for _ in range(ticks_per_day):
                self.apply_tick_price()

            self._advance_game_day()  # or whatever you use for day rollover

        print("Finished sim:", days_to_simulate, "days")

    def format_time(self, minutes):
        h = minutes // 60
        m = minutes % 60

        suffix = "AM"
        if h >= 12:
            suffix = "PM"
        if h == 0:
            h = 12
        elif h > 12:
            h -= 12

        return f"{h}:{m:02d} {suffix}"

class GameAssets:
    def __init__(self):
        self.minus_up   = pygame.image.load("assets/buttons/minus_button.png").convert_alpha()
        self.minus_down = pygame.image.load("assets/buttons/minus_button_pushed.png").convert_alpha()
        self.plus_up    = pygame.image.load("assets/buttons/plus_button.png").convert_alpha()
        self.plus_down  = pygame.image.load("assets/buttons/plus_button_pushed.png").convert_alpha()
        self.max_up = pygame.image.load("assets/buttons/max_button.png").convert_alpha()
        self.max_down = pygame.image.load("assets/buttons/max_button_pushed.png").convert_alpha()
        self.buy_button_up = pygame.image.load("assets/buttons/buy_button.png").convert_alpha()
        self.buy_button_down = pygame.image.load("assets/buttons/buy_button_pushed.png").convert_alpha()
pygame.init()
pygame.mixer.init()
screen = pygame.display.set_mode((1920,1080), pygame.DOUBLEBUF | pygame.SCALED)

clock = pygame.time.Clock()
#------------------------
# SOUNDS
#------------------------
fps_font = pygame.font.Font("assets/fonts/VCR_OSD_MONO_1.001.ttf", 18)
purchase_sound = pygame.mixer.Sound("assets/sounds/purchase_sound.mp3")
tick_sound_up = pygame.mixer.Sound("assets/sounds/tick_sound_up.wav")
tick_sound_down = pygame.mixer.Sound("assets/sounds/tick_sound_down.wav")
chart_sound = pygame.mixer.Sound("assets/sounds/chart_pop.mp3")
sale_sound = pygame.mixer.Sound("assets/sounds/sale_sound.mp3")
#------------------------
#FONTS
#------------------------
ticker_font = pygame.font.Font("assets/fonts/VCR_OSD_MONO_1.001.ttf", 16)
header_font = pygame.font.Font("assets/fonts/VCR_OSD_MONO_1.001.ttf", 20)
info_font = pygame.font.Font("assets/fonts/VCR_OSD_MONO_1.001.ttf", 20)
menu_font = pygame.font.Font("assets/fonts/VCR_OSD_MONO_1.001.ttf", 50)
sidebar_font = pygame.font.Font("assets/fonts/VCR_OSD_MONO_1.001.ttf", 50)
info_bar_font = pygame.font.Font("assets/fonts/VCR_OSD_MONO_1.001.ttf", 16)

choice = gui.render_main_menu(screen, menu_font)
#------------------------
# ART
#------------------------


pixel_cache = None
pixel_cache_timer = 0
pixel_update_rate = 4   # update every 4 frames
if choice == "quit":
    pygame.quit()
    quit()
running = True
state = GameState()
# SIMULATION FUNCTION
# state.simulate_days(365)
assets = GameAssets()
ticker_x = 1920  # start fully off-screen to the right
save_timer = 0
save_interval = 10  # seconds

backbuffer = pygame.Surface((1920, 1080))
crt_enabled = False
frame_counter = 0
scanlines = pygame.Surface((1920, 1080), pygame.SRCALPHA)
pixel_surface = pygame.Surface((1920, 1080))

PIXEL_SIZE = 1.2
for y in range(0, 1080, 3):
    pygame.draw.line(scanlines, (0, 0, 0, 45), (0, y), (1920, y))
while running:

    # -----------------------------------------------------
    # EVENT HANDLING
    # -----------------------------------------------------
    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            t0 = time.time()
            state.autosave()
            print("SAVE TIME:", time.time() - t0)
            running = False
            break  # <–– prevents zombie frame

        # ESC menu
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                choice = gui.render_pause_menu(screen, header_font,state)
                if choice == "quit":
                    state.autosave()
                    running = False
                if choice == "toggle_crt":
                    crt_enabled = not crt_enabled
            if event.key == pygame.K_b:
                s = state.selected_stock
                if s:
                    data = state.tickers[s]

                    # Ensure the price will exceed the recent high
                    if "recent_prices" not in data or len(data["recent_prices"]) < 30:
                        data["recent_prices"] = [data["current_price"] * 0.9] * 30

                    # Increase the price WAY above current high
                    old_price = data["current_price"]
                    recent_high = max(data["recent_prices"][-30:])
                    data["current_price"] = recent_high * 1.05  # guaranteed breakout

                    print("=== FORCED BREAKOUT ===")
                    print("old:", old_price, "new:", data["current_price"], "recent_high:", recent_high)
            # --- FORCE BEARISH BREAKOUT TEST ---
            if event.type == pygame.KEYDOWN and event.key == pygame.K_KP0:  # NumPad 0
                if state.selected_stock:
                    name = state.selected_stock
                    data = state.tickers[name]

                    # force price far BELOW recent low
                    recent_prices = data.get("recent_prices", [])
                    if recent_prices:
                        recent_low = min(recent_prices[-30:])
                        forced = recent_low * 0.90  # 10% breakdown

                        print("=== FORCED BEARISH BREAKDOWN ===")
                        print(f"old: {data['current_price']} new: {forced}  recent_low: {recent_low}")

                        data["current_price"] = forced
                        data["last_price"] = forced
                        recent_prices.append(forced)
                        data["recent_prices"] = recent_prices[-200:]

                        # inject news message now
                        state.news_messages.append({
                            "text": f"{name} breaks support! Bearish breakdown!",
                            "color": (255, 80, 80)
                        })

        # Chart zoom
        if event.type == pygame.MOUSEWHEEL:
            # store old zoom BEFORE changing
            state.prev_chart_zoom = state.chart_zoom

            if event.y > 0:
                state.chart_zoom *= 1.15
            else:
                state.chart_zoom /= 1.15

            state.chart_zoom = max(0.1, min(200.0, state.chart_zoom))

        # Chart pan via keys
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                state.chart_offset -= 5
            if event.key == pygame.K_RIGHT:
                state.chart_offset += 5

        # Mouse clicks
        if event.type == pygame.MOUSEBUTTONDOWN:

            # Unwarp CRT coordinates
            if crt_enabled:
                unwarped = gui.crt_unwarp(event.pos[0], event.pos[1])
                if unwarped is None:
                    continue
                mx, my = unwarped


            else:
                mx, my = event.pos


            # ==================================================
            # Candle/Chart toggle
            # ==================================================
            if state.toggle_volume_rect and state.toggle_volume_rect.collidepoint(mx, my):
                state.show_volume = not state.show_volume

            if state.toggle_candles_rect and state.toggle_candles_rect.collidepoint(mx, my):
                state.show_candles = not state.show_candles
            # ==================================================
            # PORTFOLIO SCREEN CLICKS
            # ==================================================
            if state.show_portfolio_screen:

                # BACK
                if state.portfolio_ui.get("back") and state.portfolio_ui["back"].collidepoint(mx, my):
                    state.show_portfolio_screen = False
                    continue

                # VISUALIZE
                if state.portfolio_ui.get("visualize") and state.portfolio_ui["visualize"].collidepoint(mx, my):
                    state.show_visualize_screen = True
                    state.show_portfolio_screen = False
                    continue

                # SELECT STOCK
                for stock, rect in state.portfolio_click_zones.items():
                    if rect.collidepoint(mx, my):
                        state.selected_stock = stock
                        state.show_portfolio_screen = False
                        continue

                continue  # BLOCK clicks from hitting normal UI

            # ==================================================
            # VISUALIZE SCREEN CLICKS
            # ==================================================
            if state.show_visualize_screen:

                if state.visualize_ui.get("back") and state.visualize_ui["back"].collidepoint(mx, my):
                    state.show_visualize_screen = False
                    state.show_portfolio_screen = True
                continue  # block all other clicks

            # ==================================================
            # NORMAL UI CLICKS
            # ==================================================

            # SIDEBAR BUTTONS
            if sidebar_data:
                for b in sidebar_data:
                    if b["rect"].collidepoint(mx, my):
                        if b["action"] == "view_portfolio":
                            state.show_portfolio_screen = True
                            continue
                        if b["action"] == "open_shop":
                            print("Shop")
                            continue
                        if b["action"] == "view_analysis":
                            print("Analysis")
                            continue

            # STOCK LIST
            for stock_name, rect in click_zones.items():
                if rect.collidepoint(mx, my):
                    state.selected_stock = stock_name
                    chart_sound.play()

                    if stock_name not in state.portfolio:
                        state.portfolio[stock_name] = {
                            "shares": 0,
                            "bought_at": [],
                            "sell_qty": 0
                        }

                    state.portfolio[stock_name]["sell_qty"] = 0
                    state.tickers[stock_name]["buy_qty"] = 0
                    continue

            # BUY +
            if state.add_button_buy_rect and state.add_button_buy_rect.collidepoint(mx, my):
                state.button_cooldowns["plus_buy"] = 0.08
                state.tickers[state.selected_stock]["buy_qty"] += 1
                tick_sound_up.play()

            # BUY -
            if state.minus_button_buy_rect and state.minus_button_buy_rect.collidepoint(mx, my):
                state.button_cooldowns["minus_buy"] = 0.08
                if state.tickers[state.selected_stock]["buy_qty"] > 0:
                    state.tickers[state.selected_stock]["buy_qty"] -= 1
                    tick_sound_down.play()

            # BUY MAX
            if state.max_button_buy_rect and state.max_button_buy_rect.collidepoint(mx, my):
                state.button_cooldowns["max_buy"] = 0.08
                s = state.selected_stock
                cash = state.account["money"]
                price = state.tickers[s]["current_price"]
                state.tickers[s]["buy_qty"] = math.floor(cash / price)

            # BUY
            if state.buy_button_rect and state.buy_button_rect.collidepoint(mx, my):
                state.button_cooldowns["buy"] = 0.08
                s = state.selected_stock
                before = state.portfolio[s]["shares"]
                if state.market_time >= state.market_open and state.market_time <= state.market_close:
                    state.handle_buy()
                if state.portfolio[s]["shares"] > before:
                    purchase_sound.play()

            # ==================== SELL BUTTON ====================
            if state.sell_button_rect and state.sell_button_rect.collidepoint(mx, my):
                state.button_cooldowns["sell"] = 0.10
                if state.is_market_open:
                    try:
                        state.handle_sell()
                        sale_sound.play()
                    except IndexError:
                        pass

            # ==================== SELL - BUTTON ====================
            if state.minus_button_sell_rect and state.minus_button_sell_rect.collidepoint(mx, my):
                state.button_cooldowns["minus_sell"] = 0.10
                s = state.selected_stock
                if state.portfolio[s]["sell_qty"] > 0:
                    state.portfolio[s]["sell_qty"] -= 1
                    tick_sound_down.play()

            # ==================== SELL + BUTTON ====================
            if state.add_button_sell_rect and state.add_button_sell_rect.collidepoint(mx, my):
                state.button_cooldowns["plus_sell"] = 0.10
                s = state.selected_stock
                if state.portfolio[s]["sell_qty"] < state.portfolio[s]["shares"]:
                    state.portfolio[s]["sell_qty"] += 1
                    tick_sound_up.play()

            # ==================== MAX SELL ====================
            if state.max_button_sell_rect and state.max_button_sell_rect.collidepoint(mx, my):
                state.button_cooldowns["max_sell"] = 0.10
                s = state.selected_stock
                state.portfolio[s]["sell_qty"] = math.floor(state.portfolio[s]["shares"])

    # -----------------------------------------------------
    # TICK UPDATE
    # -----------------------------------------------------
    dt = clock.tick(120) / 1000
    # Update cooldown timers
    for key in state.button_cooldowns:
        if state.button_cooldowns[key] > 0:
            state.button_cooldowns[key] -= dt

    state.tick_timer += dt
    save_timer += dt

    if save_timer >= save_interval:
        state.autosave()
        save_timer = 0

    while state.tick_timer >= state.tick_interval:
        state.apply_tick_price()
        state.tick_timer -= state.tick_interval

    state.portfolio_value = state.get_portfolio_value()
    time_left = max(0, state.tick_interval - state.tick_timer)

    # -----------------------------------------------------
    # SCREEN SWITCHING (RENDER)
    # -----------------------------------------------------

    # =================== PORTFOLIO ===================
    if state.show_portfolio_screen:
        game_surface = pygame.Surface((1920,1080))
        gui.render_portfolio_screen(game_surface, header_font, state)

        if crt_enabled:
            warped = gui.apply_crt_warp(game_surface, 0.05)
            screen.blit(warped,(0,0))
            screen.blit(scanlines,(0,0))
            gui._apply_flicker(screen)
        else:
            screen.blit(game_surface,(0,0))

        fps = int(clock.get_fps())
        screen.blit(fps_font.render(f"FPS: {fps}",True,(0,255,0)),(10,10))
        pygame.display.flip()
        continue

    # =================== VISUALIZE ===================
    if state.show_visualize_screen:
        game_surface = pygame.Surface((1920,1080))
        gui.render_visualize_screen(game_surface, header_font, state)

        if crt_enabled:
            warped = gui.apply_crt_warp(game_surface, 0.05)
            screen.blit(warped,(0,0))
            screen.blit(scanlines,(0,0))
            gui._apply_flicker(screen)
        else:
            screen.blit(game_surface,(0,0))

        fps = int(clock.get_fps())
        screen.blit(fps_font.render(f"FPS: {fps}",True,(0,255,0)),(10,10))
        pygame.display.flip()
        continue

    # =================== NORMAL MODE ===================
    game_surface = pygame.Surface((1920,1080))
    game_surface.fill((0,0,0))
    gui.render_header(header_font, state.account, game_surface, time_left, state.portfolio_value, state)
    click_zones = gui.render_tickers(ticker_font, state.tickers, game_surface)
    sidebar_data = gui.render_side_bar(game_surface, info_bar_font, state)
    gui.render_chart(info_font, state, game_surface)
    gui.render_info_panel(info_font, assets, game_surface,state)


    ticker_speed = 160
    ticker_x, ticker_zones, ticker_bar = gui.render_news_ticker(
        game_surface, ticker_font,
        state.news_messages,
        ticker_speed,
        ticker_x,
        dt
    )

    mx, my = pygame.mouse.get_pos()

    if pygame.mouse.get_pressed()[0]:
        if ticker_bar.collidepoint(mx, my):  # anywhere in bar
            for text, rect in ticker_zones.items():
                if rect.collidepoint(mx, my):
                    symbol = text.split()[0]
                    state.selected_stock = symbol
                    print("OPENED CHART FROM NEWS:", symbol)

    # CRT
    if crt_enabled:
        # 1. Apply CRT warp TO game_surface
        warped = gui.apply_crt_warp(game_surface, 0.03)

        # 2. Pixelate the WARPED result (not the original game_surface)
        apply_cached_pixelation(warped, pixel_surface, PIXEL_SIZE)

        # 3. Draw pixelated CRT to screen
        screen.blit(pixel_surface, (0, 0))
        screen.blit(scanlines, (0, 0))
    else:
        screen.blit(game_surface, (0, 0))


    # FPS
    fps = int(clock.get_fps())
    screen.blit(fps_font.render(f"FPS: {fps}",True,(0,255,0)),(10,10))
    # ---- RESET CLICK ANIMATION FLAGS ----
    state.buy_button_pressed = False
    state.minus_buy_pressed = False
    state.plus_buy_pressed = False
    state.max_buy_pressed = False

    state.sell_button_pressed = False
    state.minus_sell_pressed = False
    state.plus_sell_pressed = False
    state.max_sell_pressed = False

    pygame.display.flip()


pygame.mixer.quit()
pygame.quit()
sys.exit()


