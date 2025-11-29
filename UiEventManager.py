import pygame
import math
class UiEventManager:
    def __init__(self, state):
        self.state = state
        self.current_screen = "normal"     # normal / portfolio / visualize
        self.crt_enabled = False
        # === DRAWER (buy/sell panel) ===
        self.drawer_width = 300  # width of the whole drawer
        self.drawer_x_open = 1920 - 300  # 1620: fully visible position
        self.drawer_x_closed = 1920  # fully hidden position (off-screen right)

        # starting position (closed)
        self.drawer_x = self.drawer_x_closed

        # handle size and placement
        self.handle_width = 20
        self.handle_height = 120
        self.handle_y = 500

        # dragging state
        self.drawer_dragging = False
        self.drawer_drag_offset = 0
        self.drawer_open_x = 1620  # fully open position
        self.drawer_closed_x = 1920  # fully closed (off-screen)

        # =========================================================
        # STOCK SELECTION
        # =========================================================
        self.selected_stock = None

        # =========================================================
        # INFO PANEL TOGGLES
        # =========================================================
        self.show_volume = False
        self.show_candles = False
        self.toggle_volume_rect = None
        self.toggle_candles_rect = None

        # =========================================================
        # BUY / SELL BUTTON RECTS (old system still used elsewhere)
        # =========================================================
        # self.buy_button_rect = None
        # self.sell_button_rect = None
        # self.plus_buy_rect = None
        # self.minus_buy_rect = None
        # self.max_buy_rect = None
        # self.plus_sell_rect = None
        # self.minus_sell_rect = None
        # self.max_sell_rect = None

        # caret timing for blinking
        self.caret_timer = 0
        self.caret_visible = True

        # =========================================================
        # **********  UNIFIED ORDER INPUT SYSTEM  ***************
        # Player chooses:
        #   "Buy Market Order"
        #   "Buy Limit Order"
        #   "Sell Market Order"
        #   "Sell Limit Order"
        # =========================================================
        self.order_type = "Buy - Market Order"
        self.order_dropdown_open = False

        self.order_type_rect = None
        self.order_option_rects = []   # list of (label, rect)

        # =========================================================
        # INPUT FIELDS (shared)
        # =========================================================
        self.active_input = None       # "qty" or "limit"

        # BUY FIELDS
        self.qty_text = ""
        self.qty_caret = 0

        self.limit_text = ""
        self.limit_caret = 0

        # SELL FIELDS
        self.sell_qty_text = ""
        self.sell_qty_caret = 0

        self.sell_limit_text = ""
        self.sell_limit_caret = 0

        # Tracks which SELL field is active ("qty" or "limit")
        self.sell_active_input = None

        # rects for the rendered input fields (assigned every frame)
        self.qty_rect = None
        self.limit_rect = None
        self.sell_qty_rect = None
        self.sell_limit_rect = None

        # =========================================================
        # COOLDOWNS FOR OLD BUY/SELL BUTTONS
        # =========================================================
        # self.button_cooldowns = {
        #     "buy": 0, "plus_buy": 0, "minus_buy": 0, "max_buy": 0,
        #     "sell": 0, "plus_sell": 0, "minus_sell": 0, "max_sell": 0
        # }

        # =========================================================
        # SCREEN SWITCHING
        # =========================================================
        self.pending_switch = None
        self.just_switched = False

        # =========================================================
        # ********** CHART ANIMATION SYSTEM **********
        # =========================================================
        self.chart_animating = False
        self.chart_direction = "idle"       # "idle", "in", "out"
        self.chart_target_y = 350           # resting position
        self.chart_start_y = 1080           # off-screen bottom start
        self.chart_slide_y = self.chart_start_y

        self.old_chart_surface = None
        self.current_chart_surface = None
        self.pending_scroll = 0

        # =========================================================
        # UI Cache (populated each frame)
        # =========================================================
        self.sidebar_rects = None
        self.ticker_rects = None
        self.portfolio_rects = {}
        self.visualize_rects = {}



    # ------------------------------------------------
    # SCREEN CONTROL
    # ------------------------------------------------


    def is_screen(self, name):
        return self.current_screen == name

    # ------------------------------------------------
    # For GUI to tell UIManager what rects exist
    # ------------------------------------------------
    def register_info_panel_rects(self, info):
        self.toggle_volume_rect = info.get("toggle_volume")
        self.toggle_candles_rect = info.get("toggle_candles")

        # self.plus_buy_rect = info.get("plus_buy")
        # self.minus_buy_rect = info.get("minus_buy")
        # self.max_buy_rect = info.get("max_buy")
        # self.buy_button_rect = info.get("buy")
        #
        # self.plus_sell_rect = info.get("plus_sell")
        # self.minus_sell_rect = info.get("minus_sell")
        # self.max_sell_rect = info.get("max_sell")
        # self.sell_button_rect = info.get("sell")

    def register_sidebar(self, sidebar_data):
        self.sidebar_rects = sidebar_data

    def register_tickers(self, click_zones):
        self.ticker_rects = click_zones

    def register_portfolio(self, rects):
        self.portfolio_rects = rects

    def register_visualize(self, rects):
        self.visualize_rects = rects

    # ------------------------------------------------
    # KEY HANDLING
    # ------------------------------------------------
    def handle_key(self, event, screen, header_font):
        state = self.state

        # ============================
        # ESC → PAUSE MENU
        # ============================
        if event.key == pygame.K_ESCAPE:
            choice = state.gui_system.render_pause_menu(
                screen,
                header_font,
                state
            )

            if choice == "quit":
                state.autosave()
                return "quit"
            elif choice == "toggle_crt":
                self.crt_enabled = not self.crt_enabled

            return  # done handling ESC

        # ============================
        # ORDER ENTRY TYPING (QTY / LIMIT)
        # ============================
        if self.active_input is not None:
            # choose which field we're editing
            if self.active_input == "qty":
                text = self.qty_text
                caret = self.qty_caret
                allow_dot = False  # qty = int
            else:  # "limit"
                text = self.limit_text
                caret = self.limit_caret
                allow_dot = True  # limit price can have '.'

            handled = False

            # BACKSPACE
            if event.key == pygame.K_BACKSPACE:
                if caret > 0:
                    text = text[:caret - 1] + text[caret:]
                    caret -= 1
                handled = True

            # DELETE
            elif event.key == pygame.K_DELETE:
                if caret < len(text):
                    text = text[:caret] + text[caret + 1:]
                handled = True

            # LEFT
            elif event.key == pygame.K_LEFT:
                if caret > 0:
                    caret -= 1
                handled = True

            # RIGHT
            elif event.key == pygame.K_RIGHT:
                if caret < len(text):
                    caret += 1
                handled = True

            # ENTER – optional submit, for now just ignore
            elif event.key == pygame.K_RETURN:
                handled = True

            # NORMAL CHAR INPUT
            else:
                ch = event.unicode
                if ch.isdigit():
                    text = text[:caret] + ch + text[caret:]
                    caret += 1
                    handled = True
                elif allow_dot and ch == "." and "." not in text:
                    text = text[:caret] + ch + text[caret:]
                    caret += 1
                    handled = True

            # write back to the correct field
            if self.active_input == "qty":
                self.qty_text = text
                self.qty_caret = caret
            else:
                self.limit_text = text
                self.limit_caret = caret

            if handled:
                return  # don't fall through to other hotkeys when typing

        # ============================
        # DEBUG / TEST HOTKEYS
        # ============================

        # Force breakout (KP 0 or B)
        if event.key == pygame.K_b or event.key == pygame.K_KP0:
            if self.selected_stock:
                d = state.tickers_obj[self.selected_stock]

                if len(d.recent_prices) < 30:
                    d.recent_prices = [d.current_price * 0.9] * 30

                recent_high = max(d.recent_prices[-30:])
                d.current_price = recent_high * 1.05
                d.last_price = d.current_price
                print("=== FORCED BREAKOUT ===")
            return

        # Force breakdown (KP 1)
        if event.key == pygame.K_KP1:
            if self.selected_stock:
                d = state.tickers_obj[self.selected_stock]

                if d.recent_prices:
                    low = min(d.recent_prices[-30:])
                    forced = low * 0.90
                    d.current_price = forced
                    d.last_price = forced
                    d.recent_prices.append(forced)
                    d.recent_prices = d.recent_prices[-200:]
                    print("=== FORCED BREAKDOWN ===")
            return

        # ============================
        # CHART PANNING
        # ============================
        if event.key == pygame.K_LEFT:
            state.chart_offset -= 5
            return

        if event.key == pygame.K_RIGHT:
            state.chart_offset += 5
            return

    # ------------------------------------------------
    # MOUSE HANDLING
    # ------------------------------------------------
    def handle_mouse(self, mx, my, sidebar_data, click_zones):
        state = self.state
        if sidebar_data is None:
            sidebar_data = []

        print(f"HANDLE_MOUSE called with:, {mx}, {my}\nClick Zones:{click_zones}")
        # ======================================================================
        # UNIFIED ORDER ENTRY PANEL (BUY + SELL)
        # Dropdown, Qty, Limit, Numeric Pad
        # ======================================================================
        # HANDLE CLICKED — START DRAG
        if state.ui.drawer_handle_rect and state.ui.drawer_handle_rect.collidepoint(mx, my):
            self.drawer_dragging = True
            self.drawer_drag_offset = mx - state.ui.drawer_x
            return

        # ----------------------------------------------------------------------
        # 1. DROPDOWN OPEN → HANDLE OPTION CLICKS FIRST
        # ----------------------------------------------------------------------
        if state.ui.order_dropdown_open:

            # Click an option
            for opt_text, opt_rect in state.ui.order_option_rects:
                if opt_rect.collidepoint(mx, my):
                    # Store chosen order type
                    state.ui.order_type = opt_text
                    state.ui.order_dropdown_open = False

                    # Reset fields each selection
                    state.ui.active_input = None
                    state.ui.qty_text = ""
                    state.ui.limit_text = ""
                    state.ui.qty_caret = 0
                    state.ui.limit_caret = 0
                    return

            # Block clicking fields while dropdown is open
            if state.ui.qty_rect and state.ui.qty_rect.collidepoint(mx, my):
                return
            if state.ui.limit_rect and state.ui.limit_rect.collidepoint(mx, my):
                return

        # ----------------------------------------------------------------------
        # 2. MAIN DROPDOWN CLICK
        # ----------------------------------------------------------------------
        if state.ui.order_type_rect and state.ui.order_type_rect.collidepoint(mx, my):
            state.ui.order_dropdown_open = not state.ui.order_dropdown_open
            state.ui.active_input = None
            return

        # ----------------------------------------------------------------------
        # 3. CLICK QTY FIELD
        # ----------------------------------------------------------------------
        if (not state.ui.order_dropdown_open and
                state.ui.qty_rect and state.ui.qty_rect.collidepoint(mx, my)):

            state.ui.active_input = "qty"

            font = state.fonts["buy_input_font"]
            rel_x = mx - (state.ui.qty_rect.left + 10)

            txt = state.ui.qty_text
            caret = 0
            for i in range(len(txt) + 1):
                if font.size(txt[:i])[0] >= rel_x:
                    caret = i
                    break

            state.ui.qty_caret = caret
            return

        # ----------------------------------------------------------------------
        # 4. CLICK LIMIT FIELD (only for limit orders)
        # ----------------------------------------------------------------------
        if (not state.ui.order_dropdown_open and
                state.ui.limit_rect and state.ui.limit_rect.collidepoint(mx, my)):

            state.ui.active_input = "limit"

            font = state.fonts["buy_input_font"]
            rel_x = mx - (state.ui.limit_rect.left + 10)

            txt = state.ui.limit_text
            caret = 0
            for i in range(len(txt) + 1):
                if font.size(txt[:i])[0] >= rel_x:
                    caret = i
                    break

            state.ui.limit_caret = caret
            return

        # ----------------------------------------------------------------------
        # 5. KEYPAD BUTTONS + CONFIRM ORDER  (FIXED — NOT NESTED)
        # ----------------------------------------------------------------------

        # First: handle sidebar navigation separately
        if self.sidebar_rects:
            for b in self.sidebar_rects:
                if b["rect"].collidepoint(mx, my):

                    action = b["action"]

                    # Navigation
                    if action == "view_portfolio":
                        self.switch("portfolio")
                        return
                    if action == "open_shop":
                        print("Shop")
                        return
                    if action == "view_analysis":
                        print("Analysis")
                        return

                    # Old digit logic (keep it)
                    if action.endswith("_pressed"):
                        digit = action[0]

                        if state.ui.active_input == "qty":
                            t = state.ui.qty_text
                            c = state.ui.qty_caret
                            state.ui.qty_text = t[:c] + digit + t[c:]
                            state.ui.qty_caret += 1
                            return

                        if state.ui.active_input == "limit":
                            t = state.ui.limit_text
                            c = state.ui.limit_caret
                            state.ui.limit_text = t[:c] + digit + t[c:]
                            state.ui.limit_caret += 1
                            return

                        # default
                        t = state.ui.qty_text
                        c = state.ui.qty_caret
                        state.ui.qty_text = t[:c] + digit + t[c:]
                        state.ui.qty_caret += 1
                        return

        # ----------------------------------------------------------------------
        # Now handle the REAL keypad (num_pad_rects) — NOT inside sidebar loop
        # ----------------------------------------------------------------------
        for b in sidebar_data:
            rect = b["rect"]
            action = b["action"]

            if not rect.collidepoint(mx, my):
                continue

            # DIGITS
            if action.endswith("_pressed"):
                digit = action[0]

                if state.ui.active_input == "qty":
                    t = state.ui.qty_text
                    c = state.ui.qty_caret
                    state.ui.qty_text = t[:c] + digit + t[c:]
                    state.ui.qty_caret += 1
                    return

                if state.ui.active_input == "limit":
                    t = state.ui.limit_text
                    c = state.ui.limit_caret
                    state.ui.limit_text = t[:c] + digit + t[c:]
                    state.ui.limit_caret += 1
                    return

                # default = qty
                t = state.ui.qty_text
                c = state.ui.qty_caret
                state.ui.qty_text = t[:c] + digit + t[c:]
                state.ui.qty_caret += 1
                return

            # DOT
            if action == "._pressed":
                if state.ui.active_input == "limit" and "." not in state.ui.limit_text:
                    t = state.ui.limit_text
                    c = state.ui.limit_caret
                    state.ui.limit_text = t[:c] + "." + t[c:]
                    state.ui.limit_caret += 1
                return

            # MAX
            if action == "max_input":
                if self.selected_stock:
                    ticker = state.tickers_obj[self.selected_stock]
                    cash = state.account["money"]
                    qty = int(cash // ticker.current_price)
                    state.ui.qty_text = str(qty)
                    state.ui.qty_caret = len(state.ui.qty_text)
                return

            # CLEAR
            if action == "clear_input":
                if state.ui.active_input == "limit":
                    state.ui.limit_text = ""
                    state.ui.limit_caret = 0
                else:
                    state.ui.qty_text = ""
                    state.ui.qty_caret = 0
                return

            # CONFIRM ORDER
            if action == "confirm_order":
                # Always sync stock selection
                ticker = state.selected_stock
                self.selected_stock = ticker

                if not ticker:
                    print("NO STOCK SELECTED")
                    return
                price = state.tickers_obj[ticker].current_price
                qty = int(state.ui.qty_text) if state.ui.qty_text else 0

                if qty <= 0:
                    print("INVALID QTY")
                    return

                order_type = state.ui.order_type.lower()

                # BUY MARKET
                if order_type == "buy - market order":
                    if not state.is_market_open:
                        print("MARKET CLOSED — MARKET ORDER BLOCKED")
                        return
                    total_cost = qty * price
                    if state.account["money"] >= total_cost:
                        state.account["money"] -= total_cost
                        state.portfolio_mgr.buy_stock(ticker, qty)
                        try:
                            state.sounds["buy"].play()
                        except:
                            pass
                        print(f"BUY {qty} {ticker} @ {price:.2f}")
                    else:
                        print("NOT ENOUGH MONEY")
                    return

                # SELL MARKET
                if order_type == "sell - market order":
                    if not state.is_market_open:
                        print("MARKET CLOSED — MARKET ORDER BLOCKED")
                        return
                    shares = state.portfolio.get(ticker, {}).get("shares", 0)
                    if shares >= qty:
                        state.portfolio_mgr.sell_stock(ticker, qty)
                        try:
                            state.sounds["sell"].play()
                        except:
                            pass
                        print(f"SELL {qty} {ticker} @ {price:.2f}")
                    else:
                        print("NOT ENOUGH SHARES")
                    return

                # BUY LIMIT
                if order_type == "buy - limit order":
                    if not state.ui.limit_text:
                        print("ENTER LIMIT PRICE")
                        return

                    limit_price = float(state.ui.limit_text)

                    if state.is_market_open and price <= limit_price:
                        total_cost = qty * price
                        if state.account["money"] >= total_cost:
                            state.account["money"] -= total_cost
                            state.portfolio_mgr.buy_stock(ticker, qty)
                            print(f"BUY LIMIT EXECUTED {qty} {ticker}")
                        else:
                            print("NOT ENOUGH CASH FOR LIMIT")
                    else:
                        state.open_orders.append({
                            "ticker": ticker,
                            "side": "buy",
                            "qty": qty,
                            "limit_price": limit_price
                        })
                        print(f"BUY LIMIT PLACED {qty} {ticker} @ {limit_price}")
                    return

                # SELL LIMIT
                if order_type == "sell - limit order":
                    if not state.ui.limit_text:
                        print("ENTER LIMIT PRICE")
                        return

                    limit_price = float(state.ui.limit_text)
                    shares = state.portfolio.get(ticker, {}).get("shares", 0)

                    if shares < qty:
                        print("NOT ENOUGH SHARES")
                        return

                    if state.is_market_open and price >= limit_price:
                        state.portfolio_mgr.sell_stock(ticker, qty)
                        print(f"SELL LIMIT EXECUTED {qty} {ticker}")
                    else:
                        state.open_orders.append({
                            "ticker": ticker,
                            "side": "sell",
                            "qty": qty,
                            "limit_price": limit_price
                        })
                        print(f"SELL LIMIT PLACED {qty} {ticker} @ {limit_price}")

                    return


        # ============================================
        # PORTFOLIO SCREEN
        # ============================================
        if self.is_screen("portfolio"):

            # Back
            if self.portfolio_rects.get("back") and self.portfolio_rects["back"].collidepoint(mx, my):
                self.switch("normal")
                return

            # Visualize
            if self.portfolio_rects.get("visualize") and self.portfolio_rects["visualize"].collidepoint(mx, my):
                self.switch("visualize")
                return

            # Stock rows
            for stk, rect in self.portfolio_rects.items():
                if stk in state.tickers and rect.collidepoint(mx, my):
                    self.selected_stock = stk
                    state.selected_stock = stk
                    self.switch("normal")
                    return

            return
        # ============================================
        # VISUALIZE SCREEN
        # ============================================
        if self.is_screen("visualize"):

            # back button
            if self.visualize_rects.get("back") and self.visualize_rects["back"].collidepoint(mx, my):
                self.switch("portfolio")
                return

            # slice click
            slices = self.visualize_rects.get("slices", [])
            for s in slices:
                ang = s["start"] <= self._mouse_angle(mx, my) <= s["end"]
                if ang:
                    self.selected_stock = s["label"]
                    self.state.selected_stock = s["label"]
                    self.switch("normal")
                    return

            return






        # ============================================
        # INFO PANEL TOGGLES
        # ============================================


        if self.state.toggle_volume_rect and self.state.toggle_volume_rect.collidepoint(mx, my):

            state.show_volume = not state.show_volume
            try:
                state.sounds["chart"].play()
            except:
                pass
            return

        if self.state.toggle_candles_rect and self.state.toggle_candles_rect.collidepoint(mx, my):

            state.show_candles = not state.show_candles
            try:
                state.sounds["chart"].play()
            except:
                pass
            return

        # ============================================
        # TICKER LIST
        # ============================================
        if self.ticker_rects:
            for stk, rect in self.ticker_rects.items():
                if rect.collidepoint(mx, my):

                    old_stock = self.state.selected_stock
                    new_stock = stk

                    # CASE 1 — no stock selected yet
                    if old_stock is None:
                        # update BOTH ui.selected_stock and state.selected_stock
                        self.selected_stock = new_stock
                        self.state.selected_stock = new_stock
                        # ensure portfolio entry exists
                        if new_stock not in state.portfolio:
                            state.portfolio[new_stock] = {"shares": 0, "bought_at": [], "sell_qty": 0}

                        # Start the normal "snap UP" animation
                        ui = self.state.ui
                        ui.chart_direction = "in"
                        ui.chart_slide_y = 1080
                        ui.chart_animating = True

                        try:
                            self.state.sounds["chart"].play()
                        except:
                            pass
                        return

                    # CASE 2 — clicking same stock
                    if new_stock == old_stock:
                        return

                    # CASE 3 — switching to a new stock
                    ui = self.state.ui

                    # store old chart to slide OUT
                    ui.old_chart_surface = ui.current_chart_surface

                    # phase 1 → old chart OUT
                    ui.chart_direction = "out"
                    ui.chart_slide_y = ui.chart_target_y
                    ui.chart_animating = True

                    # Set the NEW stock but do NOT animate it yet
                    # (Phase 2 begins automatically inside chart_transition)
                    self.selected_stock = new_stock
                    self.state.selected_stock = new_stock

                    try:
                        self.state.sounds["chart"].play()
                    except:
                        pass

                    return


        # ============================================
        # NEWS TICKER
        # ============================================
        news = self.state.news
        if hasattr(news, "ticker_bar_rect") and news.ticker_bar_rect.collidepoint(mx, my):
            hit = news.handle_click(mx, my)
            if hit:

                old_stock = self.state.selected_stock
                new_stock = hit

                # CASE 1 — first ever selection
                if old_stock is None:
                    self.selected_stock = new_stock
                    self.state.selected_stock = new_stock

                    ui = self.state.ui
                    ui.chart_direction = "in"
                    ui.chart_slide_y = 1080
                    ui.chart_animating = True

                    try:
                        state.sounds["chart"].play()
                    except:
                        pass
                    return

                # CASE 2 — same stock clicked → ignore
                if new_stock == old_stock:
                    return

                # CASE 3 — selecting a *different* stock
                ui = self.state.ui

                ui.old_chart_surface = ui.current_chart_surface  # animate old OUT
                ui.chart_direction = "out"
                ui.chart_slide_y = 0
                ui.chart_animating = True

                self.selected_stock = new_stock
                self.state.selected_stock = new_stock  # <<< REQUIRED

                if new_stock not in state.portfolio:
                    state.portfolio[new_stock] = {"shares": 0, "bought_at": [], "sell_qty": 0}
                else:
                    state.portfolio[new_stock]["sell_qty"] = 0

                try:
                    state.sounds["chart"].play()
                except:
                    pass

                return

    def handle_portfolio_click(self, mx, my, state):
        # Row clicks
        for ticker, rect in state.portfolio_click_zones.items():
            if rect.collidepoint(mx, my):
                state.selected_stock = ticker
                state.show_portfolio_screen = False
                return

        # Back button
        if "back" in state.portfolio_ui:
            if state.portfolio_ui["back"].collidepoint(mx, my):
                state.show_portfolio_screen = False
                return

        # Visualize button
        if "visualize" in state.portfolio_ui:
            if state.portfolio_ui["visualize"].collidepoint(mx, my):
                state.show_visualize_screen = True
                return

    def handle_visualize_click(self, mx, my, state):
        # Back button
        if "back" in state.visualize_ui:
            if state.visualize_ui["back"].collidepoint(mx, my):
                state.show_visualize_screen = False
                state.show_portfolio_screen = True
                return

    def _mouse_angle(self, mx, my):
        cx, cy = 960, 540
        dx = mx - cx
        dy = my - cy
        a = math.degrees(math.atan2(dy, dx))
        if a < 0: a += 360
        return a

    def switch(self, screen_name):
        self.pending_switch = screen_name
        self.just_switched = True

    def handle_mouse_motion(self, mx, my, buttons):
        # Only drag when left button is held
        if self.drawer_dragging and buttons[0]:
            new_x = mx - self.drawer_drag_offset
            new_x = max(self.drawer_open_x, min(self.drawer_closed_x, new_x))
            self.drawer_x = new_x
        else:
            # Mouse released → stop dragging + snap open/closed
            if self.drawer_dragging:
                self.drawer_dragging = False
                midpoint = (self.drawer_open_x + self.drawer_closed_x) // 2
                if self.drawer_x < midpoint:
                    self.drawer_x = self.drawer_open_x
                else:
                    self.drawer_x = self.drawer_closed_x
