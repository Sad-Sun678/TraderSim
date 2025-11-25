import file_functions as ff
import random
import pygame

import gui
import math
import numpy

from gui import apply_cached_pixelation


class GameState:
    def __init__(self):
        # LOAD DATA
        self.account = ff.get_json("player","account")
        self.game_day = self.account.get("market_day", 1)
        self.portfolio = ff.get_json("player","portfolio")
        self.tickers = ff.get_json("game", "tickers")

        for name, data in self.tickers.items():
            data.setdefault("day_history", [])
            data.setdefault("volume_cap", data[
                "avg_volume"] * 12)  # <-- add this
        self.global_events = ff.get_json("game","global_events")
        self.company_events = ff.get_json("game","company_events")
        for name, data in self.tickers.items():
            data.setdefault("day_history", [])

        self.selected_stock = None
        self.buy_button_rect = None
        self.sell_button_rect = None
        self.add_button_sell_rect = None
        self.minus_button_sell_rect = None
        self.add_button_buy_rect = None
        self.minus_button_buy_rect = None
        self.max_button_buy_rect = None
        self.max_button_sell_rect = None
        self.show_portfolio_screen = False
        self.show_volume = False
        self.show_candles = False
        self.toggle_volume_rect = None
        self.toggle_candles_rect = None
        self.portfolio_click_zones = {}
        self.portfolio_ui = {}
        self.visualize_ui = {}
        self.portfolio_value = self.get_portfolio_value()
        self.show_visualize_screen = False
        self.slice_animating = False
        self.slice_anim_stock = None
        self.slice_anim_timer = 0
        self.chart_zoom = 1.0
        self.chart_offset = 0
        self.chart_dragging = False
        self.chart_drag_start_x = 0
        self.chart_offset_start = 0
        self.chart_pixels_per_index = 1  # gets updated each frame
        self.slider_pos = 100


        # TWEAK INTERVAL FOR GAME TICK SPEED
        # GAME CALENDAR (40-day year)
        self.game_season = 1  # 1–4 (Q1–Q4)
        self.day_in_season = 1  # 1–10
        self.days_per_season = 10
        self.total_seasons = 4
        self.total_days_in_year = self.days_per_season * self.total_seasons
        self.tick_interval = 2
        self.tick_timer = 0
        self.market_time = 0  # 0–1440 minutes (24h)
        self.market_open = 570  # 9:30 AM → 9*60 + 30 = 570
        self.market_close = 960  # 4:00 PM → 16*60 = 960
        self.minutes_per_tick = 5  # each game tick advances 5 minutes
        self.is_market_open = False
        self.market_time = self.account.get("market_time", 0)
        self.market_open = self.account.get("market_open", 570)  # 9:30 AM default
        self.market_close = self.account.get("market_close", 960)  # 4:00 PM default
        self.market_events = []
        self.trend_decay_rate = 0.1
        self.volatility_ranges = {
            "low":    (0.002, 0.012),
            "medium": (0.01,  0.05),
            "high":   (0.03,  0.12)
        }
        self.season_profiles = {
            1: {"trend_bias": 0.001, "volatility_mult": 1.1, "volume_mult": 1.1},
            2: {"trend_bias": 0.000, "volatility_mult": 1.0, "volume_mult": 1.0},
            3: {"trend_bias": -0.0015, "volatility_mult": 1.4, "volume_mult": 1.2},
            4: {"trend_bias": -0.0005, "volatility_mult": 1.2, "volume_mult": 1.0},
        }

        self.sector_sentiment = {}
        self.market_mood = 0.0

        sector_list = []
        for ticker in self.tickers:
            sectors = self.tickers[ticker]["sector"]
            sector_list.append(sectors)
        for sector in sector_list:
            self.sector_sentiment[sector] = 0.0
        for name, data in self.tickers.items():
            data.setdefault("day_history", [])
            data.setdefault("ohlc_buffer", [])

    def apply_tick_price(self):
        self.market_time += self.minutes_per_tick

        # rollover day at midnight
        while self.market_time >= 1440:
            self.market_time -= 1440
            self._advance_game_day()

        self.is_market_open = self.market_open <= self.market_time <= self.market_close

        for name, data in self.tickers.items():

            # --------------------------------------------
            # BASIC SHORTCUTS
            # --------------------------------------------
            base = data["base_price"]
            vol_cat = data["volatility"]
            gravity = data["gravity"]
            trend = data["trend"]

            previous_price = data["last_price"]
            current_price = data["current_price"]
            data["last_price"] = current_price

            # --------------------------------------------
            # UPDATE ATH / ATL
            # --------------------------------------------
            if data["history"]:
                hist_max = max(data["history"])
                hist_min = min(data["history"])
                data["ath"] = max(data["ath"], hist_max)
                data["atl"] = min(data["atl"], hist_min)

            # --------------------------------------------
            # 1. GENTLE MEAN REVERSION
            # --------------------------------------------
            fair_value_force = (base - current_price) * (gravity * 1.3)

            # --------------------------------------------
            # 2. MOMENTUM (price streaks)
            # --------------------------------------------
            price_diff = current_price - previous_price
            data["trend"] = data["trend"] * 0.9 + price_diff * 0.1
            momentum_force = data["trend"] * 0.01

            # --------------------------------------------
            # 3. VOLATILITY REGIME (with volume influence)
            # --------------------------------------------
            vol_map = {
                "low": 0.002,
                "medium": 0.008,
                "high": 0.025
            }

            vol_multiplier = max(0.75, min(3.0, data["volume"] / data["avg_volume"]))
            volatility_force = random.gauss(0, vol_map[vol_cat]) * vol_multiplier

            # --------------------------------------------
            # 4. ORDER PRESSURE
            # --------------------------------------------
            order_force = data["buy_qty"] * 0.0005
            data["volume"] += data["buy_qty"] * 12
            data["buy_qty"] = max(0, data["buy_qty"] - 1)

            # --------------------------------------------
            # 5. SECTOR SENTIMENT
            # --------------------------------------------
            sector_force = self.sector_sentiment.get(data["sector"], 0) * 0.003

            # --------------------------------------------
            # 6. VOLUME SIMULATION
            # --------------------------------------------
            base_vol = data["avg_volume"]
            vol = data["volume"]
            t = self.market_time

            if self.is_market_open:
                # revert slowly toward average
                vol += (base_vol - vol) * 0.05

                # random noise
                vol += random.randint(-int(base_vol * 0.04), int(base_vol * 0.04))

                # realistic intraday structure
                if 570 <= t <= 615:  # open
                    vol *= random.uniform(1.7, 3.2)
                elif 720 <= t <= 810:  # lunch
                    vol *= random.uniform(0.55, 0.85)
                elif 900 <= t <= 960:  # power hour
                    vol *= random.uniform(1.3, 2.5)

                # occasional breakout
                if random.random() < 0.015:
                    vol *= random.uniform(1.4, 3.5)

            else:
                # AFTER HOURS — realistic calm
                # drift gently toward ~10–20% of normal average volume
                target_ah = base_vol * random.uniform(0.08, 0.18)
                vol += (target_ah - vol) * 0.15

                # tiny noise only
                vol += random.randint(-int(base_vol * 0.005), int(base_vol * 0.005))

            # --------------------------------------------
            # 7. SEASONAL EFFECTS (NOW CORRECT)
            # --------------------------------------------
            season = self.game_season
            profile = self.season_profiles[season]

            # SEASON TREND SHOULD BE DIRECTIONAL, NOT MEAN REVERSION
            season_trend_force = profile["trend_bias"]  # small constant drift

            # volatility influenced by season
            volatility_force *= profile["volatility_mult"]

            # volume influenced by season
            vol *= profile["volume_mult"]
            # --------------------------------------------
            # 7. DYNAMIC VOLUME CAP (ONLY DURING MARKET HOURS)
            # --------------------------------------------
            if self.is_market_open:
                if vol > data["volume_cap"] * 0.7:
                    data["volume_cap"] *= random.uniform(1.01, 1.05)  # expand ceiling slowly
                elif vol < data["volume_cap"] * 0.3:
                    data["volume_cap"] *= random.uniform(0.97, 0.995)

                # small natural drift
                data["volume_cap"] *= random.uniform(0.999, 1.001)

            # clamp cap itself
            data["volume_cap"] = max(base_vol * 5, min(data["volume_cap"], base_vol * 40))

            # final clamp
            vol = max(150, min(vol, data["volume_cap"]))
            data["volume"] = int(vol)

            data["volume_history"].append(vol)
            if len(data["volume_history"]) > 700:
                data["volume_history"].pop(0)

            # --------------------------------------------
            # 8. MARKET NOISE
            # --------------------------------------------
            noise_force = random.gauss(0, 0.003 if self.is_market_open else 0.0004)
            # --------------------------------------------
            # 9. MARKET MOOD
            # --------------------------------------------
            if random.random() < 0.002:
                # about once every 500 ticks → 1–2 times per day
                self.market_mood = random.uniform(-0.003, 0.002)  # bear bias slightly stronger

            # global bias applied every tick
            mood_force = self.market_mood

            # --------------------------------------------
            # FINAL PRICE COMBINATION
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

            data["current_price"] = round(new_price, 2)
            # --------------------------------------------
            # BUILD OHLC CANDLES (ONE PER TIMESTAMP)
            # --------------------------------------------

            # Add newest tick into the buffer
            data["ohlc_buffer"].append(new_price)

            # Determine if we should start a NEW candle
            making_new_candle = (
                    not data["day_history"] or
                    data["day_history"][-1]["time"] != self.market_time or
                    data["day_history"][-1]["day"] != self.game_day
            )

            if making_new_candle:
                # Build candle from the buffer
                prices = data["ohlc_buffer"]

                entry = {
                    "day": self.game_day,
                    "time": self.market_time,
                    "open": prices[0],
                    "high": max(prices),
                    "low": min(prices),
                    "close": prices[-1],
                    "volume": data["volume"]
                }

                data["day_history"].append(entry)

                # IMPORTANT:
                # Keep the last tick in the buffer, because the new candle
                # continues accumulating ticks from SAME timestamp.
                data["ohlc_buffer"] = [new_price]

            else:
                # UPDATE EXISTING CANDLE
                last = data["day_history"][-1]
                prices = data["ohlc_buffer"]

                last["close"] = prices[-1]
                last["high"] = max(last["high"], max(prices))
                last["low"] = min(last["low"], min(prices))
                last["volume"] = data["volume"]

            # Trim old candles
            if len(data["day_history"]) > 700:
                data["day_history"].pop(0)

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


    def buy_stock(self, stock_name, amount=1):
        data = self.tickers[stock_name]
        price = data["current_price"]
        if self.account["money"] >= price * amount:
            self.account["money"] -= price * amount
            # portfolio update
            if stock_name not in self.portfolio:
                self.portfolio[stock_name] = {
                    "shares": 0,
                    "bought_at": []
                }
            self.portfolio[stock_name]["shares"] += amount
            for _ in range(amount):
                self.portfolio[stock_name]["bought_at"].append(price)
            print(f"Bought {amount} share(s) of {stock_name} at {price:.2f}")
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
            selected_stock = self.selected_stock
            self.buy_stock(selected_stock,self.tickers[selected_stock]["buy_qty"])
            print("handler passing to buy function")
        except NameError:
            print("Name Error")
            pass

    def handle_sell(self):
        self.sell_stock(self.selected_stock,state.portfolio[self.selected_stock]['sell_qty'])

    def market_is_open(self):
        return self.market_open <= self.market_time <= self.market_close

    def autosave(self):
        self.account["market_time"] = self.market_time
        self.account["market_open"] = self.market_open
        self.account["market_close"] = self.market_close
        self.account["market_day"] = self.game_day

        ff.write_json("game", "tickers", self.tickers)
        ff.write_json("player", "account", self.account)
        ff.write_json("player", "portfolio", self.portfolio)

    def simulate_days(self, days):
        """Fast-forward the market by a number of days for debugging."""
        minutes_per_day = 1440
        total_minutes = days * minutes_per_day

        # run ticks until we've advanced the requested time
        target_time = self.market_time + total_minutes
        start_day = self.game_day

        while (self.game_day - start_day) < days:
            self.apply_tick_price()
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
pygame.init()
pygame.mixer.init()
screen = pygame.display.set_mode((1920,1080), pygame.DOUBLEBUF | pygame.SCALED)

clock = pygame.time.Clock()
fps_font = pygame.font.Font("assets/fonts/VCR_OSD_MONO_1.001.ttf", 18)

purchase_sound = pygame.mixer.Sound("assets/sounds/purchase_sound.mp3")
tick_sound_up = pygame.mixer.Sound("assets/sounds/tick_sound_up.wav")
tick_sound_down = pygame.mixer.Sound("assets/sounds/tick_sound_down.wav")
chart_sound = pygame.mixer.Sound("assets/sounds/chart_pop.mp3")
sale_sound = pygame.mixer.Sound("assets/sounds/sale_sound.mp3")
ticker_font = pygame.font.Font("assets/fonts/VCR_OSD_MONO_1.001.ttf", 16)
header_font = pygame.font.Font("assets/fonts/VCR_OSD_MONO_1.001.ttf", 20)
info_font = pygame.font.Font("assets/fonts/VCR_OSD_MONO_1.001.ttf", 20)
menu_font = pygame.font.Font("assets/fonts/VCR_OSD_MONO_1.001.ttf", 50)
sidebar_font = pygame.font.Font("assets/fonts/VCR_OSD_MONO_1.001.ttf", 50)
info_bar_font = pygame.font.Font("assets/fonts/VCR_OSD_MONO_1.001.ttf", 16)
choice = gui.render_main_menu(screen, menu_font)
pixel_cache = None
pixel_cache_timer = 0
pixel_update_rate = 4   # update every 4 frames
if choice == "quit":
    pygame.quit()
    quit()
running = True
state = GameState()
ticker_x = 1920  # start fully off-screen to the right
save_timer = 0
save_interval = 10  # seconds
ticker_messages = [
    {"text": "BREAKING: Crystal Water Co hits ALL-TIME HIGH", "color": (0, 255, 0)},
    {"text": "MARKET UPDATE: Inflation fears cause tech pullback", "color": (255, 220, 0)},
    {"text": "ALERT: GreenCore Energy breaks support level", "color": (255, 80, 80)},
    {"text": "ECONOMY: Global demand rising for consumer goods", "color": (0, 200, 255)}
]
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
            state.autosave()
            running = False

        # ESC menu
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                choice = gui.render_pause_menu(screen, header_font,state)
                if choice == "quit":
                    state.autosave()
                    running = False
                if choice == "toggle_crt":
                    crt_enabled = not crt_enabled

        # Chart zoom
        if event.type == pygame.MOUSEWHEEL:

            # store old zoom BEFORE changing
            state.prev_chart_zoom = state.chart_zoom

            if event.y > 0:
                state.chart_zoom *= 1.15
            else:
                state.chart_zoom /= 1.15

            state.chart_zoom = max(0.1, min(8.0, state.chart_zoom))

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

            # BUY + / -
            if state.add_button_buy_rect and state.add_button_buy_rect.collidepoint(mx, my):
                state.tickers[state.selected_stock]["buy_qty"] += 1
                tick_sound_up.play()

            if state.minus_button_buy_rect and state.minus_button_buy_rect.collidepoint(mx, my):
                if state.tickers[state.selected_stock]["buy_qty"] > 0:
                    state.tickers[state.selected_stock]["buy_qty"] -= 1
                    tick_sound_down.play()

            # MAX BUY
            if state.max_button_buy_rect and state.max_button_buy_rect.collidepoint(mx, my):
                s = state.selected_stock
                cash = state.account["money"]
                price = state.tickers[s]["current_price"]
                state.tickers[s]["buy_qty"] = math.floor(cash / price)

            # BUY
            if state.buy_button_rect and state.buy_button_rect.collidepoint(mx, my):
                s = state.selected_stock
                before = state.portfolio[s]["shares"]
                if state.market_time >= state.market_open and state.market_time <= state.market_close:
                    state.handle_buy()
                if state.portfolio[s]["shares"] > before:
                    purchase_sound.play()

            # SELL
            if state.sell_button_rect and state.sell_button_rect.collidepoint(mx, my):
                if state.is_market_open:

                    state.handle_sell()
                    sale_sound.play()

            # SELL + / -
            if state.minus_button_sell_rect and state.minus_button_sell_rect.collidepoint(mx, my):
                s = state.selected_stock
                if state.portfolio[s]["sell_qty"] > 0:
                    state.portfolio[s]["sell_qty"] -= 1
                    tick_sound_down.play()

            if state.add_button_sell_rect and state.add_button_sell_rect.collidepoint(mx, my):
                s = state.selected_stock
                if state.portfolio[s]["sell_qty"] < state.portfolio[s]["shares"]:
                    state.portfolio[s]["sell_qty"] += 1
                    tick_sound_up.play()
            # MAX SELL
            if state.max_button_sell_rect and state.max_button_sell_rect.collidepoint(mx, my):
                s = state.selected_stock
                cash = state.account["money"]
                price = state.tickers[s]["current_price"]
                state.portfolio[s]["sell_qty"] = math.floor(state.portfolio[s]["shares"])
    # -----------------------------------------------------
    # TICK UPDATE
    # -----------------------------------------------------
    dt = clock.tick(120) / 1000
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
    gui.render_info_panel(info_font, state, game_surface)


    ticker_speed = 160
    ticker_x = gui.render_news_ticker(game_surface, ticker_font, ticker_messages, ticker_speed, ticker_x, dt)

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

    pygame.display.flip()


pygame.quit()
