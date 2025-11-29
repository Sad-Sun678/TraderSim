import sys
import file_functions as ff
import pygame
import time
import gui
import sqlite3
import json
from stock import Stock
from gui import apply_cached_pixelation
from candle_manager import CandleManager
from portfolio_manager import PortfolioManager
from UiEventManager import UiEventManager
from news_manager import NewsManager
from gui import GameGUI
DB_PATH = "game.db"

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
        self.sounds = {
            "chart": pygame.mixer.Sound("assets/sounds/chart_pop.mp3"),
            "buy": pygame.mixer.Sound("assets/sounds/purchase_sound.mp3"),
            "sell": pygame.mixer.Sound("assets/sounds/sale_sound.mp3"),
            "tick_up": pygame.mixer.Sound("assets/sounds/tick_sound_up.wav"),
            "tick_down": pygame.mixer.Sound("assets/sounds/tick_sound_down.wav"),
        }
        self.fonts = {
        "ticker_font": pygame.font.Font("assets/fonts/VCR_OSD_MONO_1.001.ttf", 16),
        "header_font": pygame.font.Font("assets/fonts/VCR_OSD_MONO_1.001.ttf", 20),
        "info_font": pygame.font.Font("assets/fonts/VCR_OSD_MONO_1.001.ttf", 20),
        "menu_font": pygame.font.Font("assets/fonts/VCR_OSD_MONO_1.001.ttf", 50),
        "sidebar_font": pygame.font.Font("assets/fonts/VCR_OSD_MONO_1.001.ttf", 50),
        "info_bar_font": pygame.font.Font("assets/fonts/VCR_OSD_MONO_1.001.ttf", 16),
        "buy_input_font":pygame.font.Font("assets/fonts/VCR_OSD_MONO_1.001.ttf", 16)
        }

        # =====================================================
        # 2. LOAD EVERYTHING FROM SQLITE
        # =====================================================
        self.candles = CandleManager("game.db")
        self.load_from_db()
        # ========================================
        # INIT CLASSES
        #========================================
        self.portfolio_mgr = PortfolioManager(self)
        self.ui = UiEventManager(self)
        self.gui = None  # set after GameGUI() created
        self.game_assets = GameAssets()
        self.gui_system = GameGUI()


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
        self.selected_stock = None
        self.news = NewsManager(font=self.fonts["ticker_font"])

        # UI button states
        self.buy_button_rect = None
        self.sell_button_rect = None
        self.add_button_sell_rect = None
        self.minus_button_sell_rect = None
        self.add_button_buy_rect = None
        self.minus_button_buy_rect = None
        self.max_button_buy_rect = None
        self.max_button_sell_rect = None
        self.buy_input_rect = None
        self.buy_button_pressed = False
        self.minus_buy_pressed = False
        self.plus_buy_pressed = False
        self.max_buy_pressed = False
        self.minus_sell_pressed = False
        self.plus_sell_pressed = False
        self.max_sell_pressed = False
        self.buy_input_text = ""
        self.buy_input_active = False
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
        self.portfolio_value = self.portfolio_mgr.get_portfolio_value()

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
            self.candles.add_price(
                self.tickers[ticker],
                day=self.game_day,
                time=self.market_time,
                price=stock.current_price,
                volume=stock.volume
            )

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
        for ticker, info in self.portfolio_mgr.portfolio.items():
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

import pygame
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
        self.fonts = {
        "ticker_font": pygame.font.Font("assets/fonts/VCR_OSD_MONO_1.001.ttf", 16),
        "header_font": pygame.font.Font("assets/fonts/VCR_OSD_MONO_1.001.ttf", 20),
        "info_font": pygame.font.Font("assets/fonts/VCR_OSD_MONO_1.001.ttf", 20),
        "menu_font": pygame.font.Font("assets/fonts/VCR_OSD_MONO_1.001.ttf", 50),
        "sidebar_font": pygame.font.Font("assets/fonts/VCR_OSD_MONO_1.001.ttf", 50),
        "info_bar_font": pygame.font.Font("assets/fonts/VCR_OSD_MONO_1.001.ttf", 16),
        "time_label_font":pygame.font.Font("assets/fonts/VCR_OSD_MONO_1.001.ttf", 15)
        }


pygame.init()
pygame.mixer.init()
screen = pygame.display.set_mode((1920,1080), pygame.DOUBLEBUF | pygame.SCALED)
clock = pygame.time.Clock()
fps_font = pygame.font.Font("assets/fonts/VCR_OSD_MONO_1.001.ttf", 18)

pixel_cache = None
pixel_cache_timer = 0
pixel_update_rate = 4   # update every 4 frames

running = True
state = GameState()
assets = GameAssets()
time_font = assets.fonts["time_label_font"]

gui_system = GameGUI()
state.gui = gui_system  #Gives access to UI manager
choice = gui_system.render_main_menu(screen, assets.fonts["menu_font"])
if choice == "quit":
    pygame.quit()
    quit()

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
pending_click = None

# ===========================
# MAIN LOOP
# ===========================
while running:
    # =====================================================
    # EVENT HANDLING
    # =====================================================
    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            t0 = time.time()
            state.autosave()
            print("SAVE TIME:", time.time() - t0)
            running = False
            break

        if event.type == pygame.KEYDOWN:
            result = state.ui.handle_key(event, screen, assets.fonts['header_font'])
            if result == "quit":
                running = False
                break

        if event.type == pygame.MOUSEWHEEL:
            state.prev_chart_zoom = state.chart_zoom
            state.chart_zoom *= (1.15 if event.y > 0 else 1 / 1.15)
            state.chart_zoom = max(0.1, min(200.0, state.chart_zoom))
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            buttons = pygame.mouse.get_pressed()
            state.ui.handle_mouse_motion(mx, my, buttons)

        if event.type == pygame.MOUSEBUTTONDOWN:
            if state.ui.crt_enabled:
                unwarped = gui.crt_unwarp(*event.pos)
                if unwarped is None:
                    continue
                mx, my = unwarped
            else:
                mx, my = event.pos
            pending_click = (mx, my)

    # =====================================================
    # TICK UPDATE
    # =====================================================
    dt = clock.tick(120) / 1000

    for k in state.button_cooldowns:
        if state.button_cooldowns[k] > 0:
            state.button_cooldowns[k] -= dt

    state.tick_timer += dt
    save_timer += dt

    if save_timer >= save_interval:
        state.autosave()
        save_timer = 0

    while state.tick_timer >= state.tick_interval:
        state.apply_tick_price()
        state.tick_timer -= state.tick_interval

    state.portfolio_value = state.portfolio_mgr.get_portfolio_value()
    time_left = max(0, state.tick_interval - state.tick_timer)

    # =====================================================
    # SCREEN TRANSITION HANDLING
    # =====================================================
    if state.ui.pending_switch:

        backbuffer.blit(screen, (0, 0))
        state.ui.current_screen = state.ui.pending_switch
        state.ui.pending_switch = None

        game_surface = pygame.Surface((1920, 1080))
        game_surface.fill((0, 0, 0))

        if state.ui.current_screen == "portfolio":
            gui_system.render_portfolio_screen(game_surface, assets.fonts['header_font'], state)

        elif state.ui.current_screen == "visualize":
            gui_system.render_visualize_screen(game_surface, assets.fonts['header_font'], state)

        else:
            # -------- MAIN GAME DURING SCREEN SWITCH --------
            gui_system.render_header(
                assets.fonts["header_font"],
                state.account,
                game_surface,
                time_left,
                state.portfolio_value,
                state
            )

            click_zones = gui_system.render_tickers(
                assets.fonts['ticker_font'], state.tickers_obj, game_surface
            )
            state.ui.register_tickers(click_zones)

            sidebar_data = gui_system.render_side_bar(
                game_surface, assets.fonts['info_bar_font'], state
            )
            state.ui.register_sidebar(sidebar_data)

            # ---------- BUILD CHART SURFACE ----------
            chart_surface = gui_system.render_chart_to_surface(
                state, assets, assets.fonts["info_font"], time_font
            )

            # ---------- CHART + INFO PANEL TRANSITION ----------
            gui_system.chart_transition(
                game_surface,
                chart_surface,
                state.ui,
                gui_system.render_info_panel,
                assets.fonts['info_font'],
                assets,
                state,
                time_font=time_font
            )

            # ---------- NEWS ABOVE EVERYTHING ----------
            state.news.update_and_draw(game_surface, dt)

        gui_system.screen_transition(screen, backbuffer, game_surface)
        pygame.display.flip()
        continue
    state.ui.caret_timer += dt
    if state.ui.caret_timer >= 0.5:
        state.ui.caret_timer = 0
        state.ui.caret_visible = not state.ui.caret_visible

    # =====================================================
    # NORMAL RENDERING
    # =====================================================
    game_surface = pygame.Surface((1920, 1080))
    game_surface.fill((0, 0, 0))

    # -------- PORTFOLIO --------
    if state.ui.current_screen == "portfolio":
        gui_system.render_portfolio_screen(game_surface, assets.fonts['header_font'], state)

    # -------- VISUALIZE --------
    elif state.ui.current_screen == "visualize":
        gui_system.render_visualize_screen(game_surface, assets.fonts['header_font'], state)

    # -------- MAIN GAME --------
    else:
        gui_system.render_header(
            assets.fonts["header_font"],
            state.account,
            game_surface,
            time_left,
            state.portfolio_value,
            state
        )

        click_zones = gui_system.render_tickers(
            assets.fonts['ticker_font'], state.tickers_obj, game_surface
        )
        state.ui.register_tickers(click_zones)

        sidebar_data = gui_system.render_side_bar(
            game_surface, assets.fonts['info_bar_font'], state
        )
        state.ui.register_sidebar(sidebar_data)

        # ---------- BUILD CHART SURFACE ----------
        chart_surface = gui_system.render_chart_to_surface(
            state, assets, assets.fonts["info_font"], time_font
        )

        # ---------- CHART + INFO PANEL TRANSITION ----------
        gui_system.chart_transition(
            game_surface,
            chart_surface,
            state.ui,
            gui_system.render_info_panel,
            assets.fonts['info_font'],
            assets,
            state,
            time_font=time_font
        )

        # ---------- NEWS ABOVE EVERYTHING ----------
        state.news.update_and_draw(game_surface, dt)

    # ---------- PROCESS CLICK ----------
    if pending_click:
        mx, my = pending_click
        state.ui.handle_mouse(
            mx, my,
            sidebar_data if state.ui.current_screen == "normal" else None,
            click_zones if state.ui.current_screen == "normal" else None
        )
        pending_click = None

    # ---------- CRT / NORMAL DRAW ----------
    if state.ui.crt_enabled:
        warped = gui.apply_crt_warp(game_surface, 0.03)
        apply_cached_pixelation(warped, pixel_surface, PIXEL_SIZE)
        screen.blit(pixel_surface, (0, 0))
        screen.blit(scanlines, (0, 0))
    else:
        screen.blit(game_surface, (0, 0))

    screen.blit(
        fps_font.render(f"FPS: {int(clock.get_fps())}", True, (0, 255, 0)),
        (10, 10)
    )
    pygame.display.flip()


# Shutdown
pygame.mixer.quit()
pygame.quit()
sys.exit()

