import pygame

class UIManager:
    def __init__(self, state):
        self.state = state
        self.current_screen = "normal"   # normal / portfolio / visualize
        self.crt_enabled = False

    # ----------------------------
    # SCREEN CONTROL
    # ----------------------------
    def switch(self, screen_name):
        self.current_screen = screen_name

    def is_screen(self, screen_name):
        return self.current_screen == screen_name

    # ----------------------------
    # KEY HANDLING
    # ----------------------------
    def handle_key(self, event, screen, header_font):

        # ---------- ESC MENU ----------
        if event.key == pygame.K_ESCAPE:
            # GUI lives in `state.gui`
            choice = self.state.gui.render_pause_menu(screen, header_font, self.state)

            if choice == "quit":
                self.state.autosave()
                return "quit"

            elif choice == "toggle_crt":
                self.crt_enabled = not self.crt_enabled

        # ---------- DEBUG: FORCE BREAKOUT ----------
        if event.key == pygame.K_b and self.state.selected_stock:
            d = self.state.tickers_obj[self.state.selected_stock]
            if len(d.recent_prices) < 30:
                d.recent_prices = [d.current_price * 0.9] * 30
            recent_high = max(d.recent_prices[-30:])
            d.current_price = recent_high * 1.05
            print("=== FORCED BREAKOUT ===")

        # ---------- DEBUG: FORCE BEARISH BREAKDOWN ----------
        if event.key == pygame.K_KP0 and self.state.selected_stock:
            d = self.state.tickers_obj[self.state.selected_stock]
            if d.recent_prices:
                low = min(d.recent_prices[-30:])
                forced = low * 0.90
                d.current_price = forced
                d.last_price = forced
                d.recent_prices.append(forced)
                d.recent_prices = d.recent_prices[-200:]
                self.state.news_messages.append({
                    "text": f"{self.state.selected_stock} breaks support!",
                    "color": (255, 80, 80)
                })
                print("=== FORCED BEARISH BREAKDOWN ===")

        # ---------- CHART PANNING ----------
        if event.key == pygame.K_LEFT:
            self.state.chart_offset -= 5
        if event.key == pygame.K_RIGHT:
            self.state.chart_offset += 5

        return None  # continue game

    # ----------------------------
    # MOUSE HANDLING
    # ----------------------------
    def handle_mouse(self, mx, my, sidebar_data, click_zones):
        state = self.state

        # ==========================================================
        # PORTFOLIO SCREEN
        # ==========================================================
        if self.is_screen("portfolio"):

            # BACK
            if state.portfolio_ui.get("back") and state.portfolio_ui["back"].collidepoint(mx, my):
                self.switch("normal")
                return

            # VISUALIZE
            if state.portfolio_ui.get("visualize") and state.portfolio_ui["visualize"].collidepoint(mx, my):
                self.switch("visualize")
                return

            # Select stock
            for stk, rect in state.portfolio_click_zones.items():
                if rect.collidepoint(mx, my):
                    state.selected_stock = stk
                    self.switch("normal")
                    return

            return  # block others

        # ==========================================================
        # VISUALIZE SCREEN
        # ==========================================================
        if self.is_screen("visualize"):
            if state.visualize_ui.get("back") and state.visualize_ui["back"].collidepoint(mx, my):
                self.switch("portfolio")
            return

        # ==========================================================
        # SIDEBAR BUTTONS
        # ==========================================================
        if sidebar_data:
            for b in sidebar_data:
                if b["rect"].collidepoint(mx, my):

                    if b["action"] == "view_portfolio":
                        self.switch("portfolio")

                    elif b["action"] == "open_shop":
                        print("Shop")

                    elif b["action"] == "view_analysis":
                        print("Analysis")

                    return

        # ==========================================================
        # TICKER LIST (NORMAL MODE)
        # ==========================================================
        if click_zones:
            for stk, rect in click_zones.items():
                if rect.collidepoint(mx, my):
                    state.selected_stock = stk

                    # ---- play chart click sound ----
                    try:
                        self.state.sounds["chart"].play()
                    except:
                        pass

                    # Ensure portfolio entry exists
                    if stk not in state.portfolio:
                        state.portfolio[stk] = {"shares": 0, "bought_at": [], "sell_qty": 0}
                    else:
                        state.portfolio[stk]["sell_qty"] = 0

                    return
        # ==========================================================
        # BUY / SELL BUTTONS
        # ==========================================================
        s = state.selected_stock
        if s:

            # ----- BUY PLUS -----
            if state.add_button_buy_rect and state.add_button_buy_rect.collidepoint(mx, my):
                state.button_cooldowns["plus_buy"] = 0.08
                state.tickers_obj[s].buy_qty += 1
                try: state.sounds["tick_up"].play()
                except: pass
                return

            # ----- BUY MINUS -----
            if state.minus_button_buy_rect and state.minus_button_buy_rect.collidepoint(mx, my):
                state.button_cooldowns["minus_buy"] = 0.08
                if state.tickers_obj[s].buy_qty > 0:
                    state.tickers_obj[s].buy_qty -= 1
                    try: state.sounds["tick_down"].play()
                    except: pass
                return

            # ----- MAX BUY -----
            if state.max_button_buy_rect and state.max_button_buy_rect.collidepoint(mx, my):
                state.button_cooldowns["max_buy"] = 0.08
                cash = state.account["money"]
                price = state.tickers_obj[s].current_price
                state.tickers_obj[s].buy_qty = int(cash // price)
                return

            # ----- BUY -----
            if state.buy_button_rect and state.buy_button_rect.collidepoint(mx, my):
                qty = state.tickers_obj[s].buy_qty
                if state.is_market_open and qty > 0:
                    before = state.portfolio[s]["shares"]
                    state.portfolio_mgr.buy_stock(s, qty)
                    if state.portfolio[s]["shares"] > before:
                        try: state.sounds["buy"].play()
                        except: pass
                state.button_cooldowns["buy"] = 0.08
                return

            # ----- SELL -----
            if state.sell_button_rect and state.sell_button_rect.collidepoint(mx, my):
                qty = state.portfolio[s]["sell_qty"]
                if state.is_market_open and qty > 0:
                    state.portfolio_mgr.sell_stock(s, qty)
                    try: state.sounds["sell"].play()
                    except: pass
                state.button_cooldowns["sell"] = 0.10
                return

            # ----- SELL MINUS -----
            if state.minus_button_sell_rect and state.minus_button_sell_rect.collidepoint(mx, my):
                state.button_cooldowns["minus_sell"] = 0.10
                if state.portfolio[s]["sell_qty"] > 0:
                    state.portfolio[s]["sell_qty"] -= 1
                    try: state.sounds["tick_down"].play()
                    except: pass
                return

            # ----- SELL PLUS -----
            if state.add_button_sell_rect and state.add_button_sell_rect.collidepoint(mx, my):
                state.button_cooldowns["plus_sell"] = 0.10
                if state.portfolio[s]["sell_qty"] < state.portfolio[s]["shares"]:
                    state.portfolio[s]["sell_qty"] += 1
                    try: state.sounds["tick_up"].play()
                    except: pass
                return

            # ----- MAX SELL -----
            if state.max_button_sell_rect and state.max_button_sell_rect.collidepoint(mx, my):
                state.button_cooldowns["max_sell"] = 0.10
                state.portfolio[s]["sell_qty"] = state.portfolio[s]["shares"]
                return

        # Buttons (buy/sell) remain in main loop
