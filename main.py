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

from stock import Stock
from gui import apply_cached_pixelation
from candle_manager import CandleManager

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
        self.recently_bought = {}

        # =====================================================
        # 2. LOAD EVERYTHING FROM SQLITE
        # =====================================================
        self.candles = CandleManager("game.db")

        self.load_from_db()

        # Build Stock objects from loaded ticker dicts
        self.tickers_obj = {
            name: Stock(name, attrs)
            for name, attrs in self.tickers.items()
        }

        # Sync core time values from DB
        self.game_day = self.account["market_day"]
        self.market_time = self.account["market_time"]
        self.market_open = self.account["market_open"]
        self.market_close = self.account["market_close"]

        # =====================================================
        # 3. RUNTIME FIELDS
        # =====================================================
        # order flow tracking
        for stock_name in self.tickers.keys():
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

        # UI button states
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

        # Screens
        self.show_portfolio_screen = False
        self.show_volume = False
        self.show_candles = False
        self.show_visualize_screen = False

        self.toggle_volume_rect = None
        self.toggle_candles_rect = None

        # UI draw caches
        self.portfolio_click_zones = {}
        self.portfolio_ui = {}
        self.visualize_ui = {}

        # Portfolio metrics
        self.portfolio_value = self.get_portfolio_value()

        # Pie slice animation
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

        # (Unused now, but harmless)
        self.trend_decay_rate = 0.1

        # =====================================================
        # 7. SEASONAL MODELS
        # =====================================================
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
        for stock in self.tickers_obj.values():
            self.sector_sentiment[stock.sector] = 0.0

        self.market_mood = 0.0

    def apply_tick_price(self):
        # ============================
        # 1. ADVANCE MARKET CLOCK
        # ============================
        self.market_time += self.minutes_per_tick

        # rollover into next day
        while self.market_time >= 1440:
            self.market_time -= 1440
            self._advance_game_day()

        self.is_market_open = self.market_open <= self.market_time <= self.market_close

        # ============================
        # 2. APPLY TICK TO EACH STOCK
        # ============================
        for ticker, stock in self.tickers_obj.items():
            # let the Stock object simulate itself
            stock.apply_tick(self)

            # ============================
            # 3. SYNC BACK TO DICT (DB/UI)
            # ============================
            d = self.tickers[ticker]

            d["current_price"] = stock.current_price
            d["last_price"] = stock.last_price
            d["trend"] = stock.trend
            d["volume"] = stock.volume
            d["ath"] = stock.ath
            d["atl"] = stock.atl

            # synced histories (for charts + DB save)
            d["day_history"] = stock.day_history
            d["volume_history"] = stock.volume_history
            d["recent_prices"] = stock.recent_prices

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
        total = 0
        for ticker, entry in self.portfolio.items():
            shares = entry["shares"]
            price = self.tickers_obj[ticker].current_price
            total += price * shares
        return total

    def buy_stock(self, stock_name, amount_purchased=1):
        data = self.tickers_obj[stock_name]
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

        data = self.tickers_obj[stock_name]
        price = data["current_price"]

        self.portfolio[stock_name]["shares"] -= amount
        self.account["money"] += price * amount
        self.portfolio[stock_name]["bought_at"].pop()
        print(f"Sold {amount} share(s) of {stock_name} at ${price:.2f}")


    def handle_buy(self):
        try:
            print("button clicked")
            selected_stock = self.selected_stock
            buy_qty = self.tickers_obj[selected_stock].buy_qty
            self.buy_stock(selected_stock,buy_qty)
            print("handler passing to buy function")
        except NameError:
            print("Name Error")
            pass

    def handle_sell(self):
        self.sell_stock(self.selected_stock, self.portfolio[self.selected_stock]['sell_qty'])

    def market_is_open(self):
        return self.market_open <= self.market_time <= self.market_close



    def load_from_db(self):
        """
        Load account, portfolio, tickers, and candle history from SQLite.
        Produces clean dicts that Stock() will wrap into objects.
        """

        conn = sqlite3.connect("game.db")
        cur = conn.cursor()

        # -------------------------------------------------
        # 1. ACCOUNT
        # -------------------------------------------------
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

        # -------------------------------------------------
        # 2. TICKERS (persistent DB fields)
        # -------------------------------------------------
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

        self.tickers = {}

        for row in rows:
            t = row[0]

            # Build initial ticker dict
            self.tickers[t] = {
                "ticker": t,
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

                # Runtime-only fields restored with defaults
                "volume_cap": row[13] * 12,
                "recent_prices": [],
                "volume_history": [],
                "day_history": [],
                "ohlc_buffer": [],
                "last_breakout_time": -9999
            }

        # -------------------------------------------------
        # 3. PORTFOLIO
        # -------------------------------------------------
        rows = cur.execute("""
                           SELECT ticker, shares, bought_at, sell_qty
                           FROM portfolio
                           """).fetchall()

        for ticker, shares, bought_at, sell_qty in rows:
            self.portfolio[ticker] = {
                "shares": shares,
                "bought_at": json.loads(bought_at),
                "sell_qty": sell_qty
            }

        # -------------------------------------------------
        # 4. CANDLES (OHLC history)
        # -------------------------------------------------
        self.candles.load_all(self.tickers)

        conn.close()

    def autosave(self):
        """
        Save account, portfolio, and ticker fields to SQLite.
        Candles are saved separately via save_candles_to_db().
        """

        # ---------------------------------
        # 1. Sync account with current runtime state
        # ---------------------------------
        self.account["market_time"] = self.market_time
        self.account["market_open"] = self.market_open
        self.account["market_close"] = self.market_close
        self.account["market_day"] = self.game_day

        conn = sqlite3.connect("game.db")
        cur = conn.cursor()

        # ---------------------------------
        # 2. SAVE ACCOUNT
        # ---------------------------------
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

        # ---------------------------------
        # 3. SAVE PORTFOLIO
        # ---------------------------------
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
                            info.get("sell_qty", 0),
                            ticker
                        ))

        # ---------------------------------
        # 4. SAVE TICKERS (from Stock objects)
        # ---------------------------------
        for name, stock in self.tickers_obj.items():
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
                            stock.current_price,
                            stock.last_price,
                            stock.base_price,
                            stock.volatility,
                            stock.gravity,
                            stock.trend,
                            stock.ath,
                            stock.atl,
                            stock.buy_qty,
                            stock.volume,
                            stock.avg_volume,
                            name
                        ))

        conn.commit()
        conn.close()

        # ---------------------------------
        # 5. SAVE CANDLES
        # ---------------------------------
        self.candles.save_all(self.tickers_obj)

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
                    data = state.tickers_obj[s]

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
                    data = state.tickers_obj[name]

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
                    # state.tickers_obj[stock_name]["buy_qty"] = 0
                    continue

            # BUY +
            if state.add_button_buy_rect and state.add_button_buy_rect.collidepoint(mx, my):
                state.button_cooldowns["plus_buy"] = 0.08
                state.tickers_obj[state.selected_stock].buy_qty += 1
                tick_sound_up.play()

            # BUY -
            if state.minus_button_buy_rect and state.minus_button_buy_rect.collidepoint(mx, my):
                state.button_cooldowns["minus_buy"] = 0.08
                if state.tickers_obj[state.selected_stock].buy_qty > 0:
                    state.tickers_obj[state.selected_stock].buy_qty -= 1
                    tick_sound_down.play()

            # BUY MAX
            if state.max_button_buy_rect and state.max_button_buy_rect.collidepoint(mx, my):
                state.button_cooldowns["max_buy"] = 0.08

                s = state.selected_stock
                cash = state.account["money"]

                price = state.tickers_obj[s].current_price
                state.tickers_obj[s].buy_qty = math.floor(cash / price)

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
    click_zones = gui.render_tickers(ticker_font, state.tickers_obj, game_surface)
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


