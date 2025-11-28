import random

import pygame
import math
import time
import numpy

class GameGUI:
    def __init__(self):
        # put shared GUI state here later if we want
        pass

    def render_tickers(self, font, tickers_obj, screen):
        mx, my = pygame.mouse.get_pos()
        y = 90
        x = 10
        click_zones = {}

        for name, stock in tickers_obj.items():

            # Determine price color
            if stock.current_price > stock.last_price:
                color = (0, 255, 0)
            elif stock.current_price < stock.last_price:
                color = (255, 80, 80)
            else:
                color = (255, 255, 255)

            row_rect = pygame.Rect(x, y, 150, 40)
            click_zones[name] = row_rect

            # Hover highlight
            if row_rect.collidepoint(mx, my):
                pygame.draw.rect(screen, (104, 104, 104), row_rect)

            text_surface = font.render(
                f"{stock.ticker}: ${stock.current_price:.2f}", True, color
            )
            text_rect = text_surface.get_rect()
            text_rect.centery = row_rect.centery
            text_rect.x = row_rect.x + 10

            screen.blit(text_surface, text_rect)

            y += 40

        return click_zones
    # =====================================================
    # HEADER BAR
    # =====================================================
    def render_header(self, font, account, screen, time_left, portfolio_value, state):
        # Background bar
        pygame.draw.rect(screen, (104, 104, 104), (0, 0, 1920, 80))

        # Title
        title_surface = font.render(f"TRADER VIEW  |  Day {state.game_day}", True, (0, 0, 139))
        screen.blit(title_surface, (20, 30))

        # CASH
        cash_text = f"Cash: ${account['money']:.2f}"
        cash_surface = font.render(cash_text, True, (51, 255, 0))
        screen.blit(cash_surface, (500, 30))

        # ===========================
        # MARKET CLOCK
        # ===========================
        if state:
            current_time = state.format_time(state.market_time)
            open_time = state.format_time(state.market_open)
            close_time = state.format_time(state.market_close)

            is_open = state.market_open <= state.market_time <= state.market_close
            status = "OPEN" if is_open else "CLOSED"
            status_color = (0,255,0) if is_open else (255,80,80)

            clock_text = f"{current_time}  ({status})"
            clock_surface = font.render(clock_text, True, status_color)
            screen.blit(clock_surface, (1000, 15))

            hours_text = f"{open_time} - {close_time}"
            hours_surface = font.render(hours_text, True, (200,200,255))
            screen.blit(hours_surface, (1000, 45))
        else:
            # fallback if state is missing
            tick_text = f"Next Tick: {time_left:.2f}s"
            tick_surface = font.render(tick_text, True, (255, 176, 0))
            screen.blit(tick_surface, (1000, 30))

        # PORTFOLIO VALUE
        portfolio_text = f"Portfolio Value:${portfolio_value:.2f}"
        portfolio_surface = font.render(portfolio_text, True, (51, 255, 0))
        screen.blit(portfolio_surface, (1400, 30))

    # =====================================================
    # INFO PANEL
    # =====================================================
    def render_info_panel(self, font, asset, screen, state):

        if state.ui.selected_stock is None:
            return

        stock_name = state.ui.selected_stock
        stock = state.tickers_obj[stock_name]
        portfolio = state.portfolio_mgr.portfolio

        # -------------------------
        # Position constants
        # -------------------------
        text_x = 380
        text_y = 120
        right_text_x = 760
        right_text_y = 200
        line_spacing = 40

        cluster_y = 890
        cluster_h = 50

        buy_w = 200
        sell_w = 200

        chart_x = 250
        chart_w = 1230
        chart_right = chart_x + chart_w

        buy_x = chart_x
        sell_x = chart_right - (sell_w + 120)

        minus_w = 50
        plus_w = 50

        minus_buy_x = buy_x - (minus_w + 10)
        plus_buy_x = buy_x + buy_w + 10

        minus_sell_x = sell_x - (minus_w + 10)
        plus_sell_x = sell_x + sell_w + 10

        max_buy_w = 320
        max_sell_w = 320
        max_buy_x = minus_buy_x
        max_sell_x = minus_sell_x
        max_y = cluster_y + cluster_h + 10

        # -------------------------
        # Stock Data
        # -------------------------
        name_text = stock.name
        ticker_text = stock.ticker
        sector_text = stock.sector
        price_text = stock.current_price
        volume_text = stock.volume

        qty_text = stock.buy_qty
        qty_sell_text = portfolio[stock_name]["sell_qty"]

        # Update ATH/ATL based on candle data
        if stock.day_history:
            stock.ath = max(c["high"] for c in stock.day_history)
            stock.atl = min(c["low"] for c in stock.day_history)

        # -------------------------
        # Right Column
        # -------------------------
        if stock_name in portfolio and portfolio[stock_name]["shares"] > 0:
            lst = portfolio[stock_name]["bought_at"]
            avg_price = sum(lst) / len(lst)

            right_lines = [
                f"Shares Owned : {portfolio[stock_name]['shares']}",
                f"Avg Purchase Price: ${avg_price:.2f}",
                f"Volume: {volume_text}",
            ]
        else:
            right_lines = [
                "Shares Owned: 0",
                "Avg Purchase Price: N/A",
                f"Volume: {volume_text}",
            ]

        for line in right_lines:
            surf = font.render(line, True, (255,255,255))
            screen.blit(surf, (right_text_x, right_text_y))
            right_text_y += 40

        # -------------------------
        # Left Column
        # -------------------------
        left_lines = [
            f"{name_text} ({ticker_text})",
            f"Sector: {sector_text}",
            f"Price Per Share: ${price_text:.2f}",
            f"All Time High: ${stock.ath:.2f}",
            f"All Time Low: ${stock.atl:.2f}",
            f"Trend: {stock.trend:.2f}",
        ]

        for line in left_lines:
            surf = font.render(line, True, (255,255,255))
            screen.blit(surf, (text_x, text_y))
            text_y += line_spacing

        # =========================================================================
        # BUY CLUSTER
        # =========================================================================
        buy_rect = pygame.Rect(buy_x, cluster_y, buy_w, cluster_h)
        if state.ui.button_cooldowns["buy"] > 0:
            screen.blit(asset.buy_button_down, (buy_x, cluster_y))
        else:
            screen.blit(asset.buy_button_up, (buy_x, cluster_y))

        minus_buy_rect = pygame.Rect(minus_buy_x, cluster_y, minus_w, cluster_h)
        plus_buy_rect  = pygame.Rect(plus_buy_x,  cluster_y, plus_w,  cluster_h)

        if state.ui.button_cooldowns["minus_buy"] > 0:
            screen.blit(asset.minus_down, (minus_buy_x, cluster_y))
        else:
            screen.blit(asset.minus_up, (minus_buy_x, cluster_y))

        if state.ui.button_cooldowns["plus_buy"] > 0:
            screen.blit(asset.plus_down, (plus_buy_x, cluster_y))
        else:
            screen.blit(asset.plus_up, (plus_buy_x, cluster_y))

        max_buy_rect = pygame.Rect(max_buy_x, max_y, max_buy_w, cluster_h)
        if state.ui.button_cooldowns["max_buy"] > 0:
            screen.blit(asset.max_down, (max_buy_x, max_y))
        else:
            screen.blit(asset.max_up, (max_buy_x, max_y))

        # =========================================================================
        # SELL CLUSTER
        # =========================================================================
        sell_rect = pygame.Rect(sell_x, cluster_y, sell_w, cluster_h)

        if state.ui.button_cooldowns["sell"] > 0:
            screen.blit(asset.buy_button_down, (sell_x, cluster_y))
        else:
            screen.blit(asset.buy_button_up, (sell_x, cluster_y))

        minus_sell_rect = pygame.Rect(minus_sell_x, cluster_y, minus_w, cluster_h)
        plus_sell_rect  = pygame.Rect(plus_sell_x,  cluster_y, plus_w,  cluster_h)

        if state.ui.button_cooldowns["minus_sell"] > 0:
            screen.blit(asset.minus_down, (minus_sell_x, cluster_y))
        else:
            screen.blit(asset.minus_up, (minus_sell_x, cluster_y))

        if state.ui.button_cooldowns["plus_sell"] > 0:
            screen.blit(asset.plus_down, (plus_sell_x, cluster_y))
        else:
            screen.blit(asset.plus_up, (plus_sell_x, cluster_y))

        max_sell_rect = pygame.Rect(max_sell_x, max_y, max_sell_w, cluster_h)
        if state.ui.button_cooldowns["max_sell"] > 0:
            screen.blit(asset.max_down, (max_sell_x, max_y))
        else:
            screen.blit(asset.max_up, (max_sell_x, max_y))

        # =========================================================================
        # SEND HITBOXES → UI MANAGER
        # =========================================================================
        state.ui.register_info_panel_rects({
            "buy": buy_rect,
            "plus_buy": plus_buy_rect,
            "minus_buy": minus_buy_rect,
            "max_buy": max_buy_rect,

            "sell": sell_rect,
            "plus_sell": plus_sell_rect,
            "minus_sell": minus_sell_rect,
            "max_sell": max_sell_rect,
        })

        # =========================================================================
        # TEXT LABELS
        # =========================================================================
        screen.blit(font.render(f"BUY:{qty_text}", True, (0,0,0)),
                    (buy_x + 80, cluster_y + 15))

        screen.blit(font.render("MAX", True, (0,0,0)),
                    (max_buy_x + 135, max_y + 15))

        screen.blit(font.render(f"SELL:{qty_sell_text}", True, (0,0,0)),
                    (sell_x + 80, cluster_y + 15))

        screen.blit(font.render("MAX", True, (0,0,0)),
                    (max_sell_x + 135, max_y + 15))

    def render_main_menu(self, screen, font):
        menu_running = True
        start_time = time.time()  # fade-in + animation timer

        # -----------------------------
        # Button definitions
        # -----------------------------
        buttons = [
            {"text": "START GAME", "action": "start"},
            {"text": "QUIT",       "action": "quit"}
        ]

        # Pre-render button surfaces + rects
        button_data = []
        offset = 0
        for b in buttons:
            surf = font.render(b["text"], True, (255, 255, 255))
            rect = surf.get_rect(center=(960, 450 + offset))
            offset += 120
            button_data.append({"surf": surf, "rect": rect, "action": b["action"]})

        # Fade-in surface
        fade_surface = pygame.Surface((1920, 1080))
        fade_surface.fill((0, 0, 0))

        # -----------------------------
        # MAIN MENU LOOP
        # -----------------------------
        while menu_running:
            elapsed = time.time() - start_time
            mouse_x, mouse_y = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"

                if event.type == pygame.MOUSEBUTTONDOWN:
                    for b in button_data:
                        if b["rect"].collidepoint(mouse_x, mouse_y):
                            return b["action"]

            # -----------------------------
            # BACKGROUND
            # -----------------------------
            screen.fill((0, 0, 0))

            # -----------------------------
            # FLOATING TITLE ANIMATION
            # -----------------------------
            float_offset = math.sin(elapsed * 2) * 10
            title = font.render("THIS GAME FUCKING SUCKS", True, (0, 200, 255))
            title_rect = title.get_rect(center=(960, 200 + float_offset))
            screen.blit(title, title_rect)

            # -----------------------------
            # BUTTONS + HOVER PULSE
            # -----------------------------
            for b in button_data:

                if b["rect"].collidepoint(mouse_x, mouse_y):
                    glow = int((math.sin(elapsed * 8) + 1) * 60)
                else:
                    glow = 0

                bg_color = (70 + glow, 70 + glow, 70 + glow)

                pygame.draw.rect(
                    screen,
                    bg_color,
                    b["rect"].inflate(20, 20),
                    border_radius=10
                )

                screen.blit(b["surf"], b["rect"])

            # -----------------------------
            # FADE-IN OVERLAY
            # -----------------------------
            if elapsed < 1.0:
                fade_alpha = int((1 - elapsed) * 255)
                fade_surface.set_alpha(fade_alpha)
                screen.blit(fade_surface, (0, 0))

            pygame.display.flip()

    def render_pause_menu(self, screen, font, state):
        menu_running = True
        start_time = time.time()

        # -----------------------------
        # BUTTON DEFINITIONS
        # -----------------------------
        buttons = [
            {"text": "RESUME GAME", "action": "resume"},
            {"text": "QUIT TO DESKTOP", "action": "quit"},
            {"text": "TOGGLE CRT", "action": "toggle_crt"},
        ]

        # Pre-render button surfaces
        button_data = []
        offset = 0
        for b in buttons:
            surf = font.render(b["text"], True, (255, 255, 255))
            rect = surf.get_rect(center=(960, 540 + offset))
            offset += 120
            button_data.append({"surf": surf, "rect": rect, "action": b["action"]})

        # -----------------------------
        # DARK OVERLAY
        # -----------------------------
        overlay = pygame.Surface((1920, 1080))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(140)

        # initial slider setup
        slider_rect, handle_x = self.draw_slider(overlay, font)
        dragging_slider = False

        # -----------------------------
        # MAIN PAUSE LOOP
        # -----------------------------
        while menu_running:
            elapsed = time.time() - start_time
            mouse_x, mouse_y = pygame.mouse.get_pos()

            if dragging_slider:
                handle_x = max(slider_rect.x, min(mouse_x, slider_rect.x + slider_rect.width))

            for event in pygame.event.get():

                if event.type == pygame.QUIT:
                    return "quit"

                # -----------------------------
                # BUTTON + SLIDER INPUT
                # -----------------------------
                if event.type == pygame.MOUSEBUTTONDOWN:

                    # Check slider first
                    if slider_rect.collidepoint(mouse_x, mouse_y):
                        dragging_slider = True

                    # Then buttons
                    for b in button_data:
                        if b["rect"].collidepoint(mouse_x, mouse_y):
                            return b["action"]

                if event.type == pygame.MOUSEBUTTONUP:
                    dragging_slider = False

                    # snap to nearest notch
                    total_notches = 10
                    notch_width = slider_rect.width / (total_notches - 1)

                    notch_index = round((handle_x - slider_rect.x) / notch_width)
                    notch_index = max(0, min(total_notches - 1, notch_index))

                    slider_level = notch_index + 1
                    handle_x = slider_rect.x + notch_index * notch_width

                    # convert slider level into tick speed
                    state.tick_interval = (11 - slider_level) / 10
                    state.slider_pos = handle_x

                    print(f"SLIDER LEVEL → {slider_level}")
                    print(f"Tick Interval: {state.tick_interval}")

            # -----------------------------
            # DRAWING
            # -----------------------------
            screen.blit(overlay, (0, 0))

            # title float
            float_offset = math.sin(elapsed * 2) * 10
            title = font.render("PAUSED", True, (255, 180, 0))
            title_rect = title.get_rect(center=(960, 300 + float_offset))
            screen.blit(title, title_rect)

            # slider
            slider_rect = self.draw_slider(screen, font)[0]
            self.draw_handle(screen, state.slider_pos, slider_rect)

            # buttons
            for b in button_data:

                if b["rect"].collidepoint(mouse_x, mouse_y):
                    glow = int((math.sin(elapsed * 8) + 1) * 60)
                else:
                    glow = 0

                bg_color = (70 + glow, 70 + glow, 70 + glow)

                pygame.draw.rect(
                    screen,
                    bg_color,
                    b["rect"].inflate(25, 25),
                    border_radius=12
                )

                screen.blit(b["surf"], b["rect"])

            pygame.display.flip()

    # ============================================================
    # TIMEFRAME HELPERS
    # ============================================================
    def select_timeframe_from_dx(self, dx):
        """Choose candle timeframe based on pixel width per candle."""
        if dx >= 6:
            return 5  # 5 minutes
        elif dx >= 3:
            return 15  # 15 minutes
        elif dx >= 1.5:
            return 30  # 30 minutes
        elif dx >= 0.75:
            return 60  # 1 hour
        elif dx >= 0.4:
            return 120  # 2 hours
        elif dx >= 0.2:
            return 240  # 4 hours
        else:
            return 1440  # 1 Day

    def aggregate_candles(self, candle_list, base_minutes, target_minutes):
        """Compress 5m candles into 15/30/60/etc."""
        candles_per_bucket = target_minutes // base_minutes
        aggregated = []
        buffer = []

        for c in candle_list:
            buffer.append(c)
            if len(buffer) == candles_per_bucket:
                aggregated.append({
                    "day": buffer[0]["day"],
                    "time": buffer[0]["time"],
                    "open": buffer[0]["open"],
                    "high": max(x["high"] for x in buffer),
                    "low": min(x["low"] for x in buffer),
                    "close": buffer[-1]["close"],
                    "volume": sum(x["volume"] for x in buffer)
                })
                buffer = []

        return aggregated

    def draw_slider(self,screen,font):
        GRAY = (200, 200, 200)
        WHITE = (255, 255, 255)

        slider_rect = pygame.Rect(100, 80, 400, 10)
        slider_text = font.render("SIM SPEED 1-10X",True,(0,0,0),(255,255,255))
        slider_text_rect = pygame.Rect(100,100,400,20)
        screen.blit(slider_text,slider_text_rect)
        handle_x = slider_rect.x

        # Draw bar
        pygame.draw.rect(screen, GRAY, slider_rect)

        # ---- DRAW NOTCH MARKERS (10 total) ----
        total_notches = 10
        notch_y1 = slider_rect.centery - 12
        notch_y2 = slider_rect.centery + 12

        for i in range(total_notches):
            notch_x = slider_rect.x + (i * (slider_rect.width / (total_notches - 1)))
            pygame.draw.line(screen, WHITE, (notch_x, notch_y1), (notch_x, notch_y2), 2)

        return slider_rect, handle_x
    def draw_handle(self,screen,handle_x,slider_rect):
        handle_radius = 15
        RED = (255, 0, 0)
        handle = pygame.draw.circle(screen, RED, (handle_x, slider_rect.centery), handle_radius)  # Draw handle
        return handle

    def get_slider_value(self, slider_rect,handle_x):
        return int((handle_x - slider_rect.x) / slider_rect.width * 100)  # Value from 0 to 100





    def render_chart(self,font, state, screen):
        import pygame

        if state.selected_stock is None:
            return

        # ----------------------------------------
        # CONSTANTS
        # ----------------------------------------
        chart_x      = 190
        chart_width  = 1326
        chart_y      = 350
        chart_height = 400
        vol_height   = 120

        # ----------------------------------------
        # PANEL BACKGROUND
        # ----------------------------------------
        panel_rect = pygame.Rect(chart_x - 8, 90, chart_width + 12, 350 + 420)
        pygame.draw.rect(screen, (40, 0, 80), panel_rect)

        # ----------------------------------------
        # BUTTONS (Volume / Candles)
        # ----------------------------------------
        button_y = 310
        button_x = 1040

        volume_button_rect  = pygame.Rect(button_x, button_y, 155, 30)
        candle_button_rect = pygame.Rect(button_x + 200, button_y, 155, 30)

        state.toggle_volume_rect = volume_button_rect
        state.toggle_candles_rect = candle_button_rect

        pygame.draw.rect(screen, (80, 30, 120), volume_button_rect)
        pygame.draw.rect(screen, (80, 30, 120), candle_button_rect)

        screen.blit(
            font.render(f"Volume: {'ON' if state.show_volume else 'OFF'}", True, (255, 255, 255)),
            (volume_button_rect.x + 8, volume_button_rect.y + 5)
        )
        screen.blit(
            font.render(f"Candles: {'ON' if state.show_candles else 'OFF'}", True, (255, 255, 255)),
            (candle_button_rect.x + 8, candle_button_rect.y + 5)
        )

        # ----------------------------------------
        # FETCH STOCK + HISTORY
        # ----------------------------------------
        stock = state.tickers_obj[state.selected_stock]
        history = sorted(stock.day_history, key=lambda e: (e["day"], e["time"]))

        if len(history) < 2:
            return

        max_day = history[-1]["day"]
        min_day = max_day - 6

        full_window = [e for e in history if min_day <= e["day"] <= max_day]
        total_points = len(full_window)

        if total_points < 2:
            return

        # ----------------------------------------
        # ZOOM + OFFSET
        # ----------------------------------------
        zoom = max(0.1, min(20.0, state.chart_zoom))
        state.chart_zoom = zoom

        old_zoom = getattr(state, "prev_chart_zoom", zoom)
        old_visible = max(10, min(total_points, int(total_points / old_zoom)))
        new_visible = max(10, min(total_points, int(total_points / zoom)))

        mx, my = pygame.mouse.get_pos()
        mouse_ratio = (mx - chart_x) / chart_width if chart_x <= mx <= chart_x + chart_width else 0.5

        if zoom != old_zoom:
            mouse_index = state.chart_offset + mouse_ratio * old_visible
            new_offset = int(mouse_index - new_visible * mouse_ratio)
            state.chart_offset = max(0, min(total_points - new_visible, new_offset))

        visible_entries = full_window[state.chart_offset: state.chart_offset + new_visible]
        state.prev_chart_zoom = zoom

        # ----------------------------------------
        # DX
        # ----------------------------------------
        dx = chart_width / new_visible
        # ====================================================
        # TIMEFRAME SELECTION (DYNAMIC)
        # ====================================================
        tf_minutes = self.select_timeframe_from_dx(dx)

        # Only compress candles if timeframe > 5m
        if tf_minutes != 5:
            visible_entries = self.aggregate_candles(visible_entries, 5, tf_minutes)
            # Recompute dx because candle count changed
            new_visible = len(visible_entries)
            dx = chart_width / max(new_visible, 1)

        # ----------------------------------------
        # PRICE RANGE
        # ----------------------------------------
        lowest_price  = min(p["low"] for p in visible_entries)
        highest_price = max(p["high"] for p in visible_entries)

        if highest_price == lowest_price:
            highest_price += 0.01

        price_delta = highest_price - lowest_price

        def price_to_y(p):
            return chart_y + chart_height - ((p - lowest_price) / price_delta) * chart_height

        def center_x(i):
            return chart_x + i * dx + dx * 0.5

        # ----------------------------------------
        # GRID (min/mid/max)
        # ----------------------------------------
        grid_color = (120, 50, 170)
        key_levels = [highest_price, (highest_price + lowest_price) / 2, lowest_price]

        for p in key_levels:
            y = price_to_y(p)
            pygame.draw.line(screen, grid_color, (chart_x, y), (chart_x + chart_width, y), 2)
            screen.blit(font.render(f"${p:.2f}", True, grid_color),
                        (chart_x + chart_width + 10, y - 10))

        # horizontal subdivisions
        step = price_delta / 6
        for i in range(7):
            y = price_to_y(lowest_price + step * i)
            pygame.draw.line(screen, grid_color, (chart_x, y), (chart_x + chart_width, y), 1)

        # vertical subdivisions
        if dx >= 60:   every = 1
        elif dx >= 30: every = 2
        elif dx >= 15: every = 5
        elif dx >= 7:  every = 10
        else:          every = 20

        for i in range(1, new_visible - 1, every):
            x = center_x(i)
            pygame.draw.line(screen, grid_color, (x, chart_y), (x, chart_y + chart_height), 1)

        # ----------------------------------------
        # DRAGGING
        # ----------------------------------------
        mx, my = pygame.mouse.get_pos()
        left_pressed = pygame.mouse.get_pressed()[0]

        if left_pressed and chart_x <= mx <= chart_x + chart_width and chart_y <= my <= chart_y + chart_height:
            if not state.chart_dragging:
                state.chart_dragging = True
                state.chart_drag_start_x = mx
                state.chart_offset_start = state.chart_offset

            drag_dx = mx - state.chart_drag_start_x
            shift = int(drag_dx / dx)
            max_offset = max(0, total_points - new_visible)
            state.chart_offset = max(0, min(state.chart_offset_start - shift, max_offset))
        else:
            state.chart_dragging = False

        # ----------------------------------------
        # CANDLES
        # ----------------------------------------
        if state.show_candles:
            for i, c in enumerate(visible_entries):

                x = center_x(i)
                open_y  = price_to_y(c["open"])
                close_y = price_to_y(c["close"])
                high_y  = price_to_y(c["high"])
                low_y   = price_to_y(c["low"])

                color = (0, 200, 0) if c["close"] >= c["open"] else (255, 80, 80)

                # tiny candle fallback
                if dx < 2:
                    pygame.draw.line(screen, color, (x, high_y), (x, low_y), 1)
                    continue

                body_w = 2 if dx < 5 else dx * 0.7
                body_left = x - body_w / 2
                body_top = min(open_y, close_y)
                body_h = abs(open_y - close_y)

                # wick
                pygame.draw.line(screen, color, (x, high_y), (x, low_y), 2)
                # body
                pygame.draw.rect(screen, color, (body_left, body_top, body_w, body_h))

        else:
            pts = [(center_x(i), price_to_y(e["close"])) for i, e in enumerate(visible_entries)]
            if len(pts) > 1:
                pygame.draw.lines(screen, (255, 255, 255), False, pts, 2)

        # ----------------------------------------
        # VOLUME
        # ----------------------------------------
        if state.show_volume:
            vol_y = chart_y + chart_height + 5
            pygame.draw.rect(screen, (25, 0, 40), (chart_x - 8, vol_y, chart_width + 12, vol_height))

            max_vol = max(e["volume"] for e in visible_entries) or 1

            for i, e in enumerate(visible_entries):
                x = center_x(i)
                h = (e["volume"] / max_vol) * vol_height

                if dx < 2:
                    bar_w = 1
                elif dx < 5:
                    bar_w = 2
                else:
                    bar_w = dx * 0.6

                left = x - bar_w / 2
                top = vol_y + vol_height - h
                color = (0, 180, 0) if e["close"] >= e["open"] else (200, 60, 60)

                pygame.draw.rect(screen, color, (left, top, bar_w, h))

        # ----------------------------------------
        # TOOLTIP
        # ----------------------------------------
        if chart_x <= mx <= chart_x + chart_width and chart_y <= my <= chart_y + chart_height:

            idx = int((mx - chart_x) / dx)
            idx = max(0, min(idx, len(visible_entries) - 1))
            e = visible_entries[idx]

            lines = [
                f"Day:   {e['day']}",
                f"Time:  {state.format_time(e['time'])}",
                f"Open:  ${e['open']:.2f}",
                f"High:  ${e['high']:.2f}",
                f"Low:   ${e['low']:.2f}",
                f"Close: ${e['close']:.2f}",
                f"Volume: {e['volume']:,}"
            ] if state.show_candles else [
                f"Day:   {e['day']}",
                f"Time:  {state.format_time(e['time'])}",
                f"Close: ${e['close']:.2f}",
                f"Volume: {e['volume']:,}"
            ]

            # vertical line
            pygame.draw.line(screen, (255,255,255), (mx, chart_y), (mx, chart_y + chart_height), 1)

            # highlight dot
            close_y = price_to_y(e["close"])
            pygame.draw.circle(screen, (255,255,0), (mx, int(close_y)), 6)

            # tooltip box
            padding = 8
            w = max(font.render(t, True, (255,255,255)).get_width() for t in lines) + padding*2
            h = len(lines) * font.get_height() + padding*2
            r = pygame.Rect(mx + 20, my + 20, w, h)

            pygame.draw.rect(screen, (20,20,40), r)
            pygame.draw.rect(screen, (120,0,160), r, 2)

            ty = r.y + padding
            for t in lines:
                screen.blit(font.render(t, True, (255,255,255)), (r.x + padding, ty))
                ty += font.get_height()
        return {
            "toggle_volume": volume_button_rect,
            "toggle_candles": candle_button_rect
        }

    def render_side_bar(self, screen, font, state):
        """
        Draws the sidebar and registers sidebar buttons
        into the UIManager for centralized click handling.
        """

        pygame.draw.rect(screen, (104, 104, 104), (1620, 80, 300, 940))

        buttons = [
            {"text": "View Portfolio", "action": "view_portfolio"},
            {"text": "Shop", "action": "open_shop"},
            {"text": "Market Analysis", "action": "view_analysis"},
        ]

        bar_x = 1620
        bar_y = 80
        bar_w = 300
        bar_h = 50
        padding = 100

        sidebar_rects = []

        for entry in buttons:
            rect = pygame.Rect(bar_x, bar_y, bar_w, bar_h)

            pygame.draw.rect(screen, (40, 0, 80), rect)

            text_surface = font.render(entry["text"], True, (255, 255, 255))
            text_rect = text_surface.get_rect(center=rect.center)
            screen.blit(text_surface, text_rect)

            sidebar_rects.append({
                "rect": rect,
                "action": entry["action"]
            })

            bar_y += padding

        # Tell UIManager where the sidebar buttons are
        state.ui.register_sidebar(sidebar_rects)

        return sidebar_rects

    def render_portfolio_screen(self, screen, font, state):

        state.portfolio_click_zones = {}

        pygame.draw.rect(screen, (10, 0, 30), (0, 0, 1920, 1080))

        title_surf = font.render("PORTFOLIO", True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(1920 // 2, 60))
        screen.blit(title_surf, title_rect)

        headers = ["Ticker", "Shares", "Avg Price", "Current", "Value", "P/L"]
        col_x = [200, 400, 600, 800, 1000, 1300]

        for i, h in enumerate(headers):
            txt = font.render(h, True, (200, 200, 200))
            screen.blit(txt, (col_x[i], 120))

        start_y = 170
        row_h = 50
        pad = 10

        for stock, data in state.portfolio_mgr.portfolio.items():
            shares = data["shares"]
            if shares <= 0:
                continue

            if len(data["bought_at"]) > 0:
                avg_price = sum(data["bought_at"]) / len(data["bought_at"])
            else:
                avg_price = 0

            current = state.tickers[stock]["current_price"]
            value = current * shares
            cost_basis = avg_price * shares
            pnl = value - cost_basis
            pnl_color = (0, 255, 0) if pnl >= 0 else (255, 80, 80)

            rect = pygame.Rect(150, start_y, 1500, row_h)
            pygame.draw.rect(screen, (40, 0, 80), rect)

            # Register clickable row
            state.portfolio_click_zones[stock] = rect

            ticker = state.tickers[stock]["ticker"]

            fields = [
                ticker,
                str(shares),
                f"${avg_price:.2f}",
                f"${current:.2f}",
                f"${value:.2f}",
                f"${pnl:.2f}"
            ]

            for i, f in enumerate(fields):
                color = pnl_color if i == 5 else (255, 255, 255)
                s = font.render(f, True, color)
                screen.blit(s, (col_x[i], start_y + 12))

            start_y += row_h + pad

        # BACK button
        back_rect = pygame.Rect(50, 950, 200, 60)
        pygame.draw.rect(screen, (80, 0, 120), back_rect)

        back_surf = font.render("BACK", True, (255, 255, 255))
        back_text_rect = back_surf.get_rect(center=back_rect.center)
        screen.blit(back_surf, back_text_rect)

        state.portfolio_ui["back"] = back_rect

        # VISUALIZE button
        viz_rect = pygame.Rect(260, 950, 300, 60)
        pygame.draw.rect(screen, (120, 0, 160), viz_rect)

        viz_surf = font.render("VISUALIZE", True, (255, 255, 255))
        viz_text_rect = viz_surf.get_rect(center=viz_rect.center)
        screen.blit(viz_surf, viz_text_rect)

        state.portfolio_ui["visualize"] = viz_rect

    def render_visualize_screen(self, screen, font, state):
        state.visualize_ui = {}

        # Background
        pygame.draw.rect(screen, (0, 0, 20), (0, 0, 1920, 1080))

        # Title
        title = font.render("PORTFOLIO BREAKDOWN", True, (255,255,255))
        screen.blit(title, title.get_rect(center=(1920//2, 80)))

        # Collect portfolio values
        values = []
        labels = []
        total_value = 0

        for stock, info in state.portfolio_mgr.portfolio.items():
            shares = info["shares"]
            if shares <= 0:
                continue
            current = state.tickers[stock]["current_price"]
            val = shares * current
            labels.append(stock)
            values.append(val)
            total_value += val

        if total_value == 0:
            no_data = font.render("NO DATA", True, (255, 80, 80))
            screen.blit(no_data, no_data.get_rect(center=(960, 540)))
            return

        slice_hitboxes = []

        # Pie chart parameters
        center = (960, 540)
        radius = 260
        angle_start = 0

        colors = [
            (255, 100, 100),
            (100, 255, 100),
            (100, 100, 255),
            (255, 200, 100),
            (200, 100, 255),
            (100, 255, 200),
            (255, 150, 150)
        ]

        # Draw slices
        for i, val in enumerate(values):
            portion = val / total_value
            angle_end = angle_start + portion * 360

            slice_hitboxes.append({
                "start": angle_start,
                "end": angle_end,
                "label": labels[i],
                "value": val,
                "shares": state.portfolio_mgr.portfolio[labels[i]]["shares"],
                "percent": portion * 100
            })

            steps = 64
            points = [center]
            for step in range(steps + 1):
                a = math.radians(angle_start + (angle_end - angle_start) * (step / steps))
                x = center[0] + math.cos(a) * radius
                y = center[1] + math.sin(a) * radius
                points.append((x, y))

            color = colors[i % len(colors)]
            pygame.draw.polygon(screen, color, points)

            # Pulse animation
            if state.slice_animating and state.slice_anim_stock == labels[i]:
                pulse_progress = min(state.slice_anim_timer / 0.25, 1)
                pulse_radius = radius + 20 * pulse_progress

                pulse_points = [center]
                for step in range(steps + 1):
                    a = math.radians(angle_start + (angle_end - angle_start) * (step / steps))
                    px = center[0] + math.cos(a) * pulse_radius
                    py = center[1] + math.sin(a) * pulse_radius
                    pulse_points.append((px, py))

                pygame.draw.polygon(screen, color, pulse_points)

            # Connector + label
            mid_angle = math.radians((angle_start + angle_end) / 2)

            x0 = center[0] + math.cos(mid_angle) * radius
            y0 = center[1] + math.sin(mid_angle) * radius

            x1 = center[0] + math.cos(mid_angle) * (radius + 70)
            y1 = center[1] + math.sin(mid_angle) * (radius + 70)

            LABEL_DISTANCE = 170
            x2 = x1 + LABEL_DISTANCE if math.cos(mid_angle) >= 0 else x1 - LABEL_DISTANCE
            y2 = y1

            pygame.draw.line(screen, color, (x0, y0), (x1, y1), 4)
            pygame.draw.line(screen, color, (x1, y1), (x2, y2), 4)

            label = font.render(labels[i], True, (255, 255, 255))
            label_rect = label.get_rect(midbottom=(x2, y2 - 10))
            screen.blit(label, label_rect)

            pygame.draw.line(screen, color,
                             (label_rect.left, label_rect.bottom + 4),
                             (label_rect.right, label_rect.bottom + 4), 4)

            angle_start = angle_end

        # Hover slice detection
        hovered_slice = None
        mx, my = pygame.mouse.get_pos()
        dx = mx - center[0]
        dy = my - center[1]
        dist = math.sqrt(dx * dx + dy * dy)

        if dist <= radius:
            ang = math.degrees(math.atan2(dy, dx))
            if ang < 0: ang += 360

            for s in slice_hitboxes:
                if s["start"] <= ang <= s["end"]:
                    hovered_slice = s
                    break

        # Breathing hover animation
        if hovered_slice and not state.slice_animating:
            t = pygame.time.get_ticks() / 1000.0
            pulse_offset = (math.sin(t * 2) * 5) + 10

            color = colors[labels.index(hovered_slice["label"]) % len(colors)]
            pulse_start = hovered_slice["start"]
            pulse_end = hovered_slice["end"]

            steps = 64
            pulse_points = [center]
            for step in range(steps + 1):
                a = math.radians(pulse_start + (pulse_end - pulse_start) * (step / steps))
                px = center[0] + math.cos(a) * (radius + pulse_offset)
                py = center[1] + math.sin(a) * (radius + pulse_offset)
                pulse_points.append((px, py))

            pygame.draw.polygon(screen, color, pulse_points)

        # Click animation
        if hovered_slice and pygame.mouse.get_pressed()[0] and not state.slice_animating:
            state.slice_animating = True
            state.slice_anim_stock = hovered_slice["label"]
            state.slice_anim_timer = 0

        # Animate click → open chart
        if state.slice_animating:
            state.slice_anim_timer += 0.016
            progress = min(state.slice_anim_timer / 0.35, 1)

            anim = None
            for s in slice_hitboxes:
                if s["label"] == state.slice_anim_stock:
                    anim = s
                    break

            if anim:
                color = colors[labels.index(anim["label"]) % len(colors)]
                steps = 64
                anim_points = [center]
                for step in range(steps + 1):
                    a = math.radians(anim["start"] + (anim["end"] - anim["start"]) * (step / steps))
                    px = center[0] + math.cos(a) * (radius + 30 * progress)
                    py = center[1] + math.sin(a) * (radius + 30 * progress)
                    anim_points.append((px, py))

                pygame.draw.polygon(screen, color, anim_points)

            if state.slice_anim_timer >= 0.35:
                state.selected_stock = state.slice_anim_stock
                state.slice_animating = False
                state.show_visualize_screen = False
                state.show_portfolio_screen = False
                return

        # Tooltip
        if dist <= radius:
            for s in slice_hitboxes:
                if s["start"] <= ang <= s["end"]:
                    text1 = font.render(f"{s['label']}", True, (255,255,255))
                    text2 = font.render(f"Shares: {s['shares']}", True, (255,255,255))
                    text3 = font.render(f"Value: ${s['value']:.2f}", True, (255,255,255))
                    text4 = font.render(f"{s['percent']:.1f}% of portfolio", True, (255,255,255))

                    padding = 10
                    w = max(text1.get_width(), text2.get_width(),
                            text3.get_width(), text4.get_width()) + 2*padding
                    h = text1.get_height()*4 + padding*3

                    tooltip_rect = pygame.Rect(mx+20, my+20, w, h)
                    pygame.draw.rect(screen, (20,20,40), tooltip_rect)
                    pygame.draw.rect(screen, (120,0,160), tooltip_rect, 3)

                    y = tooltip_rect.y + padding
                    for t in [text1, text2, text3, text4]:
                        screen.blit(t, (tooltip_rect.x+padding, y))
                        y += text1.get_height() + 5
                    break

        # BACK button
        back_rect = pygame.Rect(50, 950, 200, 60)
        pygame.draw.rect(screen, (120, 0, 160), back_rect)
        back_surf = font.render("BACK", True, (255,255,255))
        screen.blit(back_surf, back_surf.get_rect(center=back_rect.center))
        state.visualize_ui["back"] = back_rect




def apply_crt_warp(surface, curve_strength=0.045):
    """
    CRT CURVE
    """
    w, h = surface.get_size()

    # 1 — Scale down to simulate curvature
    scaled_w = int(w * (1 - curve_strength))
    scaled_h = int(h * (1 - curve_strength))
    scaled = pygame.transform.scale(surface, (scaled_w, scaled_h))

    # 2 — Center on black frame
    warped = pygame.Surface((w, h))
    warped.fill((0, 0, 0))
    warped.blit(scaled, ((w - scaled_w) // 2, (h - scaled_h) // 2))

    return warped

def crt_unwarp(mx, my, w=1920, h=1080, curve_strength=0.05):
    """
    Maps a warped mouse coordinate back to the original
    unwarped game_surface coordinate.
    """

    # Reverse of what apply_crt_warp does:
    unscaled_w = int(w * (1 - curve_strength))
    unscaled_h = int(h * (1 - curve_strength))

    offset_x = (w - unscaled_w) // 2
    offset_y = (h - unscaled_h) // 2

    # Check if mouse is inside the warped (scaled) region
    if not (offset_x <= mx <= offset_x + unscaled_w and
            offset_y <= my <= offset_y + unscaled_h):
        return None  # outside interactive area

    # Map back to original surface pixel
    unwarped_x = (mx - offset_x) * (w / unscaled_w)
    unwarped_y = (my - offset_y) * (h / unscaled_h)

    return int(unwarped_x), int(unwarped_y)

def _apply_scanlines(screen):
    width = 1920
    height = 1080
    scanline_surface = pygame.Surface((width, height), pygame.SRCALPHA)

    # softer, thinner CRT scanlines
    for y in range(0, height, 3):
        pygame.draw.line(scanline_surface, (0, 0, 0, 45), (0, y), (width, y))

    screen.blit(scanline_surface, (0, 0))


def apply_cached_pixelation(source_surface, cache_surface, pixel_size):
    # Only compute a new pixelated frame when needed
    small = pygame.transform.scale(
        source_surface,
        (source_surface.get_width() // pixel_size,
         source_surface.get_height() // pixel_size)
    )
    pygame.transform.scale(small, source_surface.get_size(), cache_surface)


def _apply_flicker(screen):
    # subtle vertical refresh-rate flicker
    if random.random() < 0.002:
        flicker_surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        flicker_surface.fill((255, 255, 255, 8))
        screen.blit(flicker_surface, (0, 0))


def _apply_glow(screen):

   #phosphor bloom

    w, h = screen.get_size()
    glow = pygame.transform.smoothscale(screen, (int(w * 0.92), int(h * 0.92)))
    glow = pygame.transform.smoothscale(glow, (w, h))
    glow.set_alpha(50)   # softer glow bloom
    screen.blit(glow, (0, 0))




def _add_rolling_static(screen, height, width, intensity):
    # Very subtle RF noise like analog TV
    static_chance = {"minimum": 0.00008, "medium": 0.02, "maximum": 0.05}.get(intensity, 0.01)

    static_surface = pygame.Surface((width, height), pygame.SRCALPHA)

    for y in range(0, height, 8):
        if random.random() < static_chance:
            alpha = random.randint(15, 40)
            pygame.draw.line(static_surface, (255, 255, 255, alpha), (0, y), (width, y))

    screen.blit(static_surface, (0, 0), special_flags=pygame.BLEND_ADD)
scanline_y = 0
