import random

import pygame
import math
import time
import numpy


def render_tickers(font, tickers, screen):
    mx, my = pygame.mouse.get_pos()
    y = 90
    x = 10
    click_zones = {}

    for stock in tickers:
        data = tickers[stock]
        if "buy_qty" not in data:
            data["buy_qty"] = 1
        if data["current_price"] > data["last_price"]:
            text_color = (0,255,0)
        elif data["current_price"] < data["last_price"]:
            text_color = (255,80,80)
        else:
            text_color = (255,255,255)

        row_rect = pygame.Rect(x, y, 150, 40)
        click_zones[stock] = row_rect

        if row_rect.collidepoint(mx, my):
            pygame.draw.rect(screen, (104,104,104), row_rect)

        text_surface = font.render(f"{data['ticker']}: ${data['current_price']:.2f}", True, text_color)
        text_rect = text_surface.get_rect()

        text_rect.centery = row_rect.centery
        text_rect.x = row_rect.x + 10
        screen.blit(text_surface, text_rect)

        y += 40
    return click_zones


def render_header(font, account, screen, time_left, portfolio_value,state):
    pygame.draw.rect(screen, (104, 104, 104), (0, 0, 1920, 80))

    title_surface = font.render(f"TRADER VIEW  |  Day {state.game_day}", True, (0, 0, 139))
    screen.blit(title_surface, (20, 30))


    # CASH
    cash_text = f"Cash: ${account['money']:.2f}"
    cash_surface = font.render(cash_text, True, (51, 255, 0))
    screen.blit(cash_surface, (500, 30))

    # ===========================
    # MARKET CLOCK (NEW)
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
        # fallback in case header is called without state
        tick_text = f"Next Tick: {time_left:.2f}s"
        tick_surface = font.render(tick_text, True, (255, 176, 0))
        screen.blit(tick_surface, (1000, 30))

    # PORTFOLIO VALUE
    portfolio_text = f"Portfolio Value:${portfolio_value:.2f}"
    portfolio_surface = font.render(portfolio_text,True,(51,255,0))
    screen.blit(portfolio_surface,(1400,30))

def render_info_panel(font, state, screen):
    if state.selected_stock is None:
        return
    else:
        # chart constants used for alignment


        stock_name = state.selected_stock
        data = state.tickers[stock_name]
        portfolio = state.portfolio

        text_x = 380
        text_y = 120
        right_text_x = 760
        right_text_y = 200
        line_spacing = 40

        # NEW POSITIONS
        cluster_y = 890
        cluster_h = 50

        buy_w = 200
        sell_w = 200

        # chart constants used for alignment
        chart_x = 250
        chart_w = 1230
        chart_right = chart_x + chart_w#1480

        buy_x = chart_x
        sell_x = chart_right - (sell_w + 120) #1280

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

        name_text = data["name"]
        ticker_text = data["ticker"]
        sector_text = data["sector"]
        price_text = data["current_price"]
        high_text = data["ath"]
        low_text = data["atl"]
        trend_text = data["trend"]
        qty_text = data["buy_qty"]
        qty_sell_text = state.portfolio[stock_name]["sell_qty"]
        volume_text = data["volume"]
        # UPDATE ATH / ATL from day_history (OHLC candles)
        if data["day_history"]:
            hist_high = max(candle["high"] for candle in data["day_history"])
            hist_low = min(candle["low"] for candle in data["day_history"])
            data["ath"] = hist_high
            data["atl"] = hist_low

        if stock_name in portfolio and portfolio[stock_name]["shares"] > 0:
            lst = portfolio[stock_name]["bought_at"]
            avg_price = sum(lst) / len(lst)
            right_lines = [
                f"Shares Owned : {portfolio[stock_name]['shares']} ",
                f"Avg Purchase Price: ${avg_price:.2f}",
                f"Volume:{volume_text}"
            ]
        else:
            right_lines = ["Shares Owned: 0", "Avg Purchase Price: N/A",
                f"Volume:{volume_text}"]

        lines = [
            f"{name_text} ({ticker_text})",
            f"Sector: {sector_text}",
            f"Price Per Share: ${price_text:.2f}",
            f"All Time High: ${high_text:.2f}",
            f"All Time Low: ${low_text:.2f}",
            f"Trend: {trend_text:.2f}"
        ]

        # draw info text
        for line in right_lines:
            surf = font.render(line, True, (255, 255, 255))
            screen.blit(surf, (right_text_x, right_text_y))
            right_text_y += 40

        for line in lines:
            surf = font.render(line, True, (255, 255, 255))
            screen.blit(surf, (text_x, text_y))
            text_y += line_spacing

        # BUY cluster
        buy_rect = pygame.Rect(buy_x, cluster_y, buy_w, cluster_h)
        pygame.draw.rect(screen, (0, 200, 80), buy_rect)

        minus_buy_rect = pygame.Rect(minus_buy_x, cluster_y, minus_w, cluster_h)
        plus_buy_rect = pygame.Rect(plus_buy_x, cluster_y, plus_w, cluster_h)

        pygame.draw.rect(screen, (231, 22, 255), minus_buy_rect)
        pygame.draw.rect(screen, (255, 216, 25), plus_buy_rect)

        max_buy_rect = pygame.Rect(max_buy_x, max_y, max_buy_w, cluster_h)
        pygame.draw.rect(screen, (93, 226, 231), max_buy_rect)

        # SELL cluster
        sell_rect = pygame.Rect(sell_x, cluster_y, sell_w, cluster_h)
        pygame.draw.rect(screen, (200, 80, 80), sell_rect)

        minus_sell_rect = pygame.Rect(minus_sell_x, cluster_y, minus_w, cluster_h)
        plus_sell_rect = pygame.Rect(plus_sell_x, cluster_y, plus_w, cluster_h)

        pygame.draw.rect(screen, (231, 22, 255), minus_sell_rect)
        pygame.draw.rect(screen, (255, 216, 25), plus_sell_rect)

        max_sell_rect = pygame.Rect(max_sell_x, max_y, max_sell_w, cluster_h)
        pygame.draw.rect(screen, (93, 226, 231), max_sell_rect)

        # register button hitboxes


        state.add_button_buy_rect = plus_buy_rect
        state.minus_button_buy_rect = minus_buy_rect
        state.buy_button_rect = buy_rect
        state.max_button_buy_rect = max_buy_rect

        state.add_button_sell_rect = plus_sell_rect
        state.minus_button_sell_rect = minus_sell_rect
        state.sell_button_rect = sell_rect
        state.max_button_sell_rect = max_sell_rect

        # text overlays
        screen.blit(font.render("-", True, (0, 0, 0)),
                    (minus_buy_x + 20, cluster_y + 15))
        screen.blit(font.render("+", True, (0, 0, 0)),
                    (plus_buy_x + 20, cluster_y + 15))
        screen.blit(font.render(f"BUY:{qty_text}", True, (0, 0, 0)),
                    (buy_x + 80, cluster_y + 15))
        screen.blit(font.render("MAX", True, (0, 0, 0)),
                    (max_buy_x + 135, max_y + 15))

        screen.blit(font.render("-", True, (0, 0, 0)),
                    (minus_sell_x + 20, cluster_y + 15))
        screen.blit(font.render("+", True, (0, 0, 0)),
                    (plus_sell_x + 20, cluster_y + 15))
        screen.blit(font.render(f"SELL:{qty_sell_text}", True, (0, 0, 0)),
                    (sell_x + 80, cluster_y + 15))
        screen.blit(font.render("MAX", True, (0, 0, 0)),
                    (max_sell_x + 135, max_y + 15))

def render_chart(font, state, screen):
    import pygame

    if state.selected_stock is None:
        return

    # =====================================================
    # CONSTANTS
    # =====================================================
    chart_x = 190
    chart_w = 1230
    chart_y = 350
    chart_h = 300

    panel_rect = pygame.Rect(chart_x, 90, chart_w, chart_h + 420)
    pygame.draw.rect(screen, (40, 0, 80), panel_rect)

    stock = state.selected_stock
    data = state.tickers[stock]

    # =====================================================
    # TIMEFRAME BUTTONS & TOGGLES
    # =====================================================
    button_y = 310
    button_x = 1040

    volume_btn = pygame.Rect(button_x, button_y, 155, 30)
    candles_btn = pygame.Rect(button_x + 200, button_y, 155, 30)

    state.toggle_volume_rect = volume_btn
    state.toggle_candles_rect = candles_btn

    # Draw toggles
    pygame.draw.rect(screen, (80, 30, 120), volume_btn)
    pygame.draw.rect(screen, (80, 30, 120), candles_btn)

    screen.blit(font.render(
        "Volume: ON" if state.show_volume else "Volume: OFF",
        True, (255, 255, 255)),
        (volume_btn.x + 8, volume_btn.y + 5))

    screen.blit(font.render(
        "Candles: ON" if state.show_candles else "Candles: OFF",
        True, (255, 255, 255)),
        (candles_btn.x + 8, candles_btn.y + 5))

    # Timeframe buttons
    labels = ["1D", "5D", "1H", "15M"]
    tf_x = chart_x + 20
    tf_y = 95
    bw, bh = 70, 30
    state.timeframe_buttons = {}

    for i, tf in enumerate(labels):
        r = pygame.Rect(tf_x + i * (bw + 10), tf_y, bw, bh)
        state.timeframe_buttons[tf] = r
        pygame.draw.rect(screen,
                         (200, 100, 255) if state.chart_timeframe == tf else (80, 30, 120),
                         r)
        txt = font.render(tf, True, (255, 255, 255))
        screen.blit(txt, (r.x + (bw - txt.get_width()) // 2, r.y + 5))

    # =====================================================
    # BUILD WINDOW DATA ACCORDING TO TIMEFRAME
    # =====================================================
    tf = state.chart_timeframe
    day_history = sorted(data["day_history"], key=lambda e: (e["day"], e["time"]))

    # ---------------- TICK STREAM SETUP ----------------
    recent = data["recent_prices"]
    recent_times = []
    mt = state.market_time
    minutes_per_tick = state.minutes_per_tick

    # Make times align backward
    for i in range(len(recent)):
        t = mt - (len(recent) - 1 - i) * minutes_per_tick
        recent_times.append(t)

    def clamp(val, lo, hi):
        return max(lo, min(val, hi))

    # Build candles from ticks
    def build_tick_candles(chunk_minutes):
        if len(recent) < 1:
            return []

        candles = []
        group_size = max(1, chunk_minutes // minutes_per_tick)

        idx = 0
        while idx < len(recent):
            group = recent[idx:idx + group_size]
            times = recent_times[idx:idx + group_size]

            c = {
                "day": state.game_day,
                "time": int(times[-1]),
                "open": group[0],
                "high": max(group),
                "low": min(group),
                "close": group[-1],
                "volume": data["volume"]
            }
            candles.append(c)
            idx += group_size

        return candles[-200:]

    if tf == "15M":
        window_data = build_tick_candles(15)

    elif tf == "1H":
        window_data = build_tick_candles(60)

    elif tf == "1D":
        if day_history:
            last_day = day_history[-1]["day"]
            window_data = [e for e in day_history if e["day"] == last_day]
        else:
            window_data = []

    elif tf == "5D":
        if day_history:
            last_day = day_history[-1]["day"]
            window_data = [e for e in day_history if last_day - 4 <= e["day"] <= last_day]
        else:
            window_data = []

    else:
        window_data = day_history[-100:]

    if len(window_data) < 2:
        return

    # =====================================================
    # ZOOM & PAN
    # =====================================================
    total_points = len(window_data)
    visible_count = max(2, min(total_points, int(total_points / state.chart_zoom)))

    # Zoom centering fix
    if getattr(state, "prev_chart_zoom", None) != state.chart_zoom:
        old_zoom = getattr(state, "prev_chart_zoom", state.chart_zoom)
        old_vis = max(2, min(total_points, int(total_points / old_zoom)))

        mx = pygame.mouse.get_pos()[0]
        mouse_ratio = (mx - chart_x) / chart_w if chart_x <= mx <= chart_x + chart_w else 0.5

        mouse_index = state.chart_offset + mouse_ratio * old_vis
        new_offset = int(mouse_index - visible_count * mouse_ratio)

        state.chart_offset = max(0, min(total_points - visible_count, new_offset))
        state.prev_chart_zoom = state.chart_zoom

    # Final window slice
    window = window_data[state.chart_offset: state.chart_offset + visible_count]

    # =====================================================
    # PRICE SCALE
    # =====================================================
    if state.show_candles:
        min_price = min(e["low"] for e in window)
        max_price = max(e["high"] for e in window)
    else:
        min_price = min(e["close"] for e in window)
        max_price = max(e["close"] for e in window)

    if max_price == min_price:
        max_price += 0.01

    dx = chart_w / (len(window) - 1)
    state.chart_pixels_per_index = dx

    # =====================================================
    # DRAGGING
    # =====================================================
    mx, my = pygame.mouse.get_pos()
    mouse_down = pygame.mouse.get_pressed()[0]
    inside_chart = chart_x <= mx <= chart_x + chart_w and chart_y <= my <= chart_y + chart_h

    if mouse_down and inside_chart:
        if not state.chart_dragging:
            state.chart_dragging = True
            state.chart_drag_start_x = mx
            state.chart_offset_start = state.chart_offset

        drag_dx = mx - state.chart_drag_start_x
        shift = int(drag_dx / dx)
        state.chart_offset = max(0, min(state.chart_offset_start - shift,
                                       total_points - visible_count))
    else:
        state.chart_dragging = False

    # ================================================================================
    # DRAW GRIDLINES
    # ================================================================================
    grid_color = (120, 50, 170)

    def price_to_y(p):
        return chart_y + chart_h - (p - min_price) / (max_price - min_price) * chart_h

    for val in [max_price, (max_price + min_price) / 2, min_price]:
        y = price_to_y(val)
        pygame.draw.line(screen, grid_color, (chart_x, y), (chart_x + chart_w, y), 2)
        screen.blit(font.render(f"${val:.2f}", True, grid_color),
                    (chart_x + chart_w + 10, y - 10))

    # =====================================================
    # DRAW CANDLES
    # =====================================================
    def center_x(i):
        return chart_x + i * dx

    if state.show_candles:
        for i, e in enumerate(window):
            x = center_x(i)

            # Clamp candle X so it can NEVER leave the chart box
            x = clamp(x, chart_x + 2, chart_x + chart_w - 2)

            y_open = price_to_y(e["open"])
            y_close = price_to_y(e["close"])
            y_high = price_to_y(e["high"])
            y_low = price_to_y(e["low"])

            color = (0, 200, 0) if e["close"] >= e["open"] else (255, 80, 80)

            # Clamp width too — prevent giant fat candles
            bw = min(dx * 0.6, 30)  # <- HARD WIDTH CAP
            bw = max(bw, 2)  # <- still keep 2px minimum

            # wick
            pygame.draw.line(screen, color, (x, y_high), (x, y_low), 2)

            # body
            body_top = min(y_open, y_close)
            body_h = abs(y_open - y_close)

            # clamp the left/right edges of the body rectangle
            left = clamp(x - bw / 2, chart_x + 1, chart_x + chart_w - bw - 1)

            pygame.draw.rect(screen, color, (left, body_top, bw, body_h))
    else:
        # line
        for i in range(len(window)-1):
            x1 = center_x(i)
            x2 = center_x(i+1)
            y1 = price_to_y(window[i]["close"])
            y2 = price_to_y(window[i+1]["close"])
            pygame.draw.line(screen, (0,255,200), (x1, y1), (x2, y2), 2)

    # =====================================================
    # VOLUME
    # =====================================================
    volume_h = 120
    volume_y = chart_y + chart_h + 40

    if state.show_volume:
        min_v = min(e["volume"] for e in window)
        max_v = max(e["volume"] for e in window) or 1

        for i, e in enumerate(window):
            x = center_x(i)
            v = e["volume"]
            prev_close = window[i-1]["close"] if i > 0 else e["close"]
            color = (0,200,0) if e["close"] >= prev_close else (255,80,80)

            norm = (v - min_v) / (max_v - min_v)
            bh = norm * volume_h
            y = volume_y + (volume_h - bh)

            bw = max(min(dx * 0.6, dx - 2), 2)
            pygame.draw.rect(screen, color, (x - bw/2, y, bw, bh))

    # =====================================================
    # TIME & DAY LABELS
    # =====================================================
    time_y = volume_y + volume_h + 20
    day_y = time_y + 20

    last_tx = -999

    for i, e in enumerate(window):
        x = center_x(i)

        label = state.format_time(e["time"])
        ts = font.render(label, True, grid_color)

        if x - last_tx >= ts.get_width() + 50:
            screen.blit(ts, (x - ts.get_width() // 2, time_y))
            last_tx = x

        # DAY LABEL
        if i > 0 and e["day"] != window[i-1]["day"]:
            ds = font.render(f"Day {e['day']}", True, (255,180,0))
            screen.blit(ds, (x - ds.get_width() // 2, day_y))

    # =====================================================
    # TOOLTIP
    # =====================================================
    mx, my = pygame.mouse.get_pos()

    if chart_x <= mx <= chart_x + chart_w and chart_y <= my <= chart_y + chart_h:
        idx = max(0, min(int((mx - chart_x) / dx), len(window)-1))
        e = window[idx]

        tp = [
            f"Day {e['day']}",
            f"Time: {state.format_time(e['time'])}",
            f"Open:  ${e['open']:.2f}",
            f"High:  ${e['high']:.2f}",
            f"Low:   ${e['low']:.2f}",
            f"Close: ${e['close']:.2f}",
            f"Volume: {e['volume']:,}"
        ]

        px = mx
        py = price_to_y(e["close"])

        pygame.draw.line(screen, (255,255,255), (px, chart_y), (px, chart_y + chart_h), 1)
        pygame.draw.circle(screen, (255,255,0), (px, int(py)), 6)

        pad = 8
        tw = max(font.render(t, True, (255,255,255)).get_width() for t in tp) + pad*2
        th = len(tp) * font.get_height() + pad*2

        rect = pygame.Rect(mx + 20, my + 20, tw, th)
        pygame.draw.rect(screen, (20,20,40), rect)
        pygame.draw.rect(screen, (120,0,160), rect, 2)

        ly = rect.y + pad
        for t in tp:
            screen.blit(font.render(t, True, (255,255,255)), (rect.x+pad, ly))
            ly += font.get_height()

def render_main_menu(screen, font):
    menu_running = True
    start_time = time.time()  # For fade-in + animations

    # Button definitions
    buttons = [
        {"text": "START GAME", "action": "start"},
        {"text": "QUIT",        "action": "quit"}
    ]

    # Pre-render buttons
    button_data = []
    offset = 0
    for b in buttons:
        surf = font.render(b["text"], True, (255, 255, 255))
        rect = surf.get_rect(center=(960, 450 + offset))
        offset += 120
        button_data.append({"surf": surf, "rect": rect, "action": b["action"]})

    # FADE-IN SURFACE
    fade_surface = pygame.Surface((1920, 1080))
    fade_surface.fill((0, 0, 0))

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

        # BACKGROUND
        screen.fill((0, 0, 0))

        # TITLE FLOAT ANIMATION
        float_offset = math.sin(elapsed * 2) * 10  # 10px up/down
        title = font.render("THIS GAME FUCKING SUCKS", True, (0, 200, 255))
        title_rect = title.get_rect(center=(960, 200 + float_offset))
        screen.blit(title, title_rect)


        # BUTTONS WITH HOVER ANIMATION

        for b in button_data:

            # Hover glow
            if b["rect"].collidepoint(mouse_x, mouse_y):
                glow = int((math.sin(elapsed * 8) + 1) * 60)  # 0–120 brightness pulse
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

        # FADE-IN EFFECT
        if elapsed < 1.0:
            fade_alpha = int((1 - elapsed) * 255)
            fade_surface.set_alpha(fade_alpha)
            screen.blit(fade_surface, (0, 0))

        pygame.display.flip()

def render_pause_menu(screen, font,state):
    menu_running = True
    start_time = time.time()  # For fade/animation timing

    buttons = [
        {"text": "RESUME GAME", "action": "resume"},
        {"text": "QUIT TO DESKTOP", "action": "quit"},
        {"text":"TOGGLE CRT", "action":"toggle_crt"},

    ]

    # Pre-render button surfaces
    button_data = []
    offset = 0
    for b in buttons:
        surf = font.render(b["text"], True, (255, 255, 255))
        rect = surf.get_rect(center=(960, 540 + offset))
        offset += 120
        button_data.append({"surf": surf, "rect": rect, "action": b["action"]})

    # Dark overlay for paused effect
    overlay = pygame.Surface((1920, 1080))
    overlay.fill((0, 0, 0))
    overlay.set_alpha(140)
    slider_rect, handle_x = draw_slider(overlay,font)  # INITIAL DEFAULT POSITION
    dragging_slider = False

    while menu_running:
        elapsed = time.time() - start_time
        mouse_x, mouse_y = pygame.mouse.get_pos()
        if dragging_slider:
            handle_x = max(slider_rect.x, min(mouse_x, slider_rect.x + slider_rect.width))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"

            if event.type == pygame.MOUSEBUTTONDOWN:
                if slider_rect.collidepoint(mouse_x, mouse_y):
                    dragging_slider = True

                for b in button_data:
                    if b["rect"].collidepoint(mouse_x, mouse_y):
                        return b["action"]

            if event.type == pygame.MOUSEBUTTONUP:
                state.tick_interval
                dragging_slider = False

                #snap handle to nearest notch
                total_notches = 10
                notch_width = slider_rect.width / (total_notches - 1)

                # compute the nearest notch index (0–9)
                notch_index = round((handle_x - slider_rect.x) / notch_width)

                # clamp for safety
                notch_index = max(0, min(total_notches - 1, notch_index))

                # convert to levels 1–10
                slider_level = notch_index + 1

                # snap handle to exact notch pos
                handle_x = slider_rect.x + notch_index * notch_width

                print(f"SLIDER LEVEL → {slider_level}")
                state.tick_interval = (11 - slider_level) / 10
                state.slider_pos = handle_x
                print(f"Tick Interval: {state.tick_interval}")



        # DRAW PAUSE OVERLAY
        screen.blit(overlay, (0, 0))

        # TITLE (floating animation)
        float_offset = math.sin(elapsed * 2) * 10
        title = font.render("PAUSED", True, (255, 180, 0))
        title_rect = title.get_rect(center=(960, 300 + float_offset))
        screen.blit(title, title_rect)

        # SLIDER
        slider_rect = draw_slider(overlay,font)[0]  # only need rect for drawing
        handle = draw_handle(screen, state.slider_pos, slider_rect)

        # BUTTONS
        for b in button_data:

            # Hover pulse
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

def draw_slider(screen,font):
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
def draw_handle(screen,handle_x,slider_rect):
    handle_radius = 15
    RED = (255, 0, 0)
    handle = pygame.draw.circle(screen, RED, (handle_x, slider_rect.centery), handle_radius)  # Draw handle
    return handle

def get_slider_value(slider_rect,handle_x):
    return int((handle_x - slider_rect.x) / slider_rect.width * 100)  # Value from 0 to 100


def render_news_ticker(screen, font, messages, speed, offset, dt):
    w, h = screen.get_size()
    bar_height = 60

    ticker_bar_rect = pygame.Rect(0, h - bar_height, w, bar_height)
    pygame.draw.rect(screen, (104, 104, 104), ticker_bar_rect)

    if not messages:
        return offset, {}, ticker_bar_rect

    click_zones = {}

    # Pre-render
    separator = "   |   "
    sep_surf = font.render(separator, True, (230, 230, 230))

    rendered = []
    for item in messages:
        surf = font.render(item["text"], True, item["color"])
        rendered.append((surf, item))
        rendered.append((sep_surf, None))

    # Draw
    x = offset
    y = h - bar_height + (bar_height // 2 - rendered[0][0].get_height() // 2)

    for surf, msg in rendered:
        w_s = surf.get_width()
        screen.blit(surf, (int(x), y))

        if msg:
            click_zones[msg["text"]] = pygame.Rect(int(x), h - bar_height, w_s, bar_height)

        x += w_s

    total_width = x - offset

    # Move ticker
    offset -= speed * dt

    # remove after leaving screen
    if messages:
        first_width = rendered[0][0].get_width()
        if offset < -first_width:
            messages.pop(0)
            # shift offset forward by that width for alignment
            offset += first_width

    # Loop
    if offset <= -total_width:
        offset = w

    return offset, click_zones, ticker_bar_rect






def render_side_bar(screen, font, state):
    side_bar_rect = pygame.draw.rect(screen, (104, 104, 104), (1620, 80, 300, 940))

    buttons = [
        {"text": "View Portfolio", "action": "view_portfolio"},
        {"text": "Shop", "action": "open_shop"},
        {"text": "Market Analysis", "action": "view_analysis"}
    ]

    button_data = []
    bar_x = 1620
    bar_y = 80
    bar_w = 300
    bar_h = 50
    padding = 100

    for line in buttons:
        rect = pygame.Rect(bar_x, bar_y, bar_w, bar_h)
        pygame.draw.rect(screen, (40, 0, 80), rect)
        # pygame.draw.rect(screen, (255, 0, 0), rect, 2)  # draw hitbox outline

        text_surface = font.render(line["text"], True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=rect.center)
        screen.blit(text_surface, text_rect)

        button_data.append({
            "rect": rect,
            "action": line["action"]
        })

        bar_y += padding

    return button_data


def render_portfolio_screen(screen, font, state):
    # Clear old zones
    state.portfolio_click_zones = {}

    # Background
    pygame.draw.rect(screen, (10, 0, 30), (0, 0, 1920, 1080))

    # Title
    title_surf = font.render("PORTFOLIO", True, (255, 255, 255))
    title_rect = title_surf.get_rect(center=(1920 // 2, 60))
    screen.blit(title_surf, title_rect)

    # Column headers
    headers = ["Ticker", "Shares", "Avg Price", "Current", "Value", "P/L"]
    col_x = [200, 400, 600, 800, 1000, 1300]

    for i, h in enumerate(headers):
        txt = font.render(h, True, (200, 200, 200))
        screen.blit(txt, (col_x[i], 120))

    # Rows
    start_y = 170
    row_h = 50
    pad = 10

    for stock, data in state.portfolio.items():
        shares = data["shares"]

        if shares <= 0:
            continue

        # avg buy
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

        # Click zone
        state.portfolio_click_zones[stock] = rect
        ticker = state.tickers[stock]["ticker"]
        # Draw text for row
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
def render_visualize_screen(screen, font, state):
    state.visualize_ui = {}

    # Background
    pygame.draw.rect(screen, (0, 0, 20), (0, 0, 1920, 1080))

    # Title
    title = font.render("PORTFOLIO BREAKDOWN", True, (255,255,255))
    screen.blit(title, title.get_rect(center=(1920//2, 80)))

    # Gather pie data
    values = []
    labels = []
    total_value = 0

    for stock, info in state.portfolio.items():
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

    # Pie chart params
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

    # Draw slices + labels
    for i, val in enumerate(values):
        portion = val / total_value
        angle_end = angle_start + portion * 360

        # save hitbox for hover detection
        slice_hitboxes.append({
            "start": angle_start,
            "end": angle_end,
            "label": labels[i],
            "value": val,
            "shares": state.portfolio[labels[i]]["shares"],
            "percent": portion * 100
        })

        # ---- DRAW SLICE ----
        steps = 64
        points = [center]
        for step in range(steps + 1):
            a = math.radians(angle_start + (angle_end - angle_start) * (step / steps))
            x = center[0] + math.cos(a) * radius
            y = center[1] + math.sin(a) * radius
            points.append((x, y))

        color = colors[i % len(colors)]
        pygame.draw.polygon(screen, color, points)

        # ---------- PULSE ANIMATION HERE ----------
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

        # ---- LABELS / CONNECTORS ----
        mid_angle = math.radians((angle_start + angle_end) / 2)

        x0 = center[0] + math.cos(mid_angle) * radius
        y0 = center[1] + math.sin(mid_angle) * radius

        x1 = center[0] + math.cos(mid_angle) * (radius + 70)
        y1 = center[1] + math.sin(mid_angle) * (radius + 70)

        LABEL_DISTANCE = 170
        if math.cos(mid_angle) >= 0:
            x2 = x1 + LABEL_DISTANCE
        else:
            x2 = x1 - LABEL_DISTANCE
        y2 = y1

        pygame.draw.line(screen, color, (x0, y0), (x1, y1), 4)
        pygame.draw.line(screen, color, (x1, y1), (x2, y2), 4)

        label = font.render(labels[i], True, (255, 255, 255))
        label_rect = label.get_rect(midbottom=(x2, y2 - 10))
        screen.blit(label, label_rect)

        underline_start = (label_rect.left, label_rect.bottom + 4)
        underline_end   = (label_rect.right, label_rect.bottom + 4)
        pygame.draw.line(screen, color, underline_start, underline_end, 4)

        angle_start = angle_end

    # ===========================
    # DETECT HOVERED SLICE
    # ===========================
    hovered_slice = None
    mx, my = pygame.mouse.get_pos()
    dx = mx - center[0]
    dy = my - center[1]
    dist = math.sqrt(dx * dx + dy * dy)

    if dist <= radius:
        ang = math.degrees(math.atan2(dy, dx))
        if ang < 0:
            ang += 360

        for s in slice_hitboxes:
            if s["start"] <= ang <= s["end"]:
                hovered_slice = s
                break

    # ===========================
    # HOVER "BREATHING" ANIMATION
    # ===========================
    if hovered_slice and not state.slice_animating:

        # slow, smooth breathing (pulse between +4 and +14)
        t = pygame.time.get_ticks() / 1000.0
        pulse_offset = (math.sin(t * 2) * 5) + 10  # slow wave

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

    # ===========================
    # CLICK: START ANIMATION
    # ===========================
    mouse_pressed = pygame.mouse.get_pressed()[0]

    if hovered_slice and mouse_pressed and not state.slice_animating:
        state.slice_animating = True
        state.slice_anim_stock = hovered_slice["label"]
        state.slice_anim_timer = 0

    # ===========================
    # CLICK ANIMATION PROGRESSION
    # ===========================
    if state.slice_animating:
        state.slice_anim_timer += 0.016  # rough 60fps step
        progress = min(state.slice_anim_timer / 0.35, 1)  # slower now

        # find slice being animated
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

        # when animation completes open the stock
        if state.slice_anim_timer >= 0.35:
            state.selected_stock = state.slice_anim_stock
            state.slice_animating = False
            state.show_visualize_screen = False
            state.show_portfolio_screen = False
            return

    # ===========================
    # TOOLTIP HOVER LOGIC
    # ===========================


    if dist <= radius:
        ang = math.degrees(math.atan2(dy, dx))
        if ang < 0: ang += 360

        for s in slice_hitboxes:
            if s["start"] <= ang <= s["end"]:
                text1 = font.render(f"{s['label']}", True, (255,255,255))
                text2 = font.render(f"Shares: {s['shares']}", True, (255,255,255))
                text3 = font.render(f"Value: ${s['value']:.2f}", True, (255,255,255))
                text4 = font.render(f"{s['percent']:.1f}% of portfolio", True, (255,255,255))

                padding = 10
                w = max(text1.get_width(), text2.get_width(), text3.get_width(), text4.get_width()) + 2*padding
                h = text1.get_height()*4 + padding*3

                tooltip_rect = pygame.Rect(mx+20, my+20, w, h)
                pygame.draw.rect(screen, (20,20,40), tooltip_rect)
                pygame.draw.rect(screen, (120,0,160), tooltip_rect, 3)

                y = tooltip_rect.y + padding
                for t in [text1, text2, text3, text4]:
                    screen.blit(t, (tooltip_rect.x+padding, y))
                    y += text1.get_height() + 5
                break

    # BACK BUTTON
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


# def _add_glitch_effect(height, width, glitch_surface, intensity):
#     # Rare horizontal slicing glitches
#     shift = {"minimum": 6, "medium": 16, "maximum": 32}.get(intensity, 10)
#
#     if random.random() < 0.3:  # 0.3% chance
#         y_start = random.randint(0, height - 25)
#         slice_height = random.randint(4, 12)
#         offset = random.randint(-shift, shift)
#
#         slice_area = pygame.Rect(0, y_start, width, slice_height)
#         slice_copy = glitch_surface.subsurface(slice_area).copy()
#         glitch_surface.blit(slice_copy, (offset, y_start))
#
#
# def _add_color_separation(screen, glitch_surface, intensity):
#     # Authentic CRT RGB misalignment (rare)
#     shift = {"minimum": 0, "medium": 2, "maximum": 5}.get(intensity, 2)
#
#     if random.random() < 0.00003:
#         for i in range(3):
#             x_off = random.randint(-shift, shift)
#             y_off = random.randint(-shift, shift)
#
#             layer = glitch_surface.copy()
#             layer.fill((0, 0, 0))
#             layer.blit(glitch_surface, (x_off, y_off))
#
#             screen.blit(layer, (0, 0), special_flags=pygame.BLEND_ADD)
#

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
