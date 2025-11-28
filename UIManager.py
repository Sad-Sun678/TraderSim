import pygame

class UIManager:
    def __init__(self, state):
        self.state = state
        self.current_screen = "normal"     # normal / portfolio / visualize
        self.crt_enabled = False

        # ==== UI STATE MOVED OUT OF GAMESTATE ====
        self.selected_stock = None

        # info-panel toggles
        self.show_volume = False
        self.show_candles = False
        self.toggle_volume_rect = None
        self.toggle_candles_rect = None

        # buy / sell buttons
        self.buy_button_rect = None
        self.sell_button_rect = None
        self.plus_buy_rect = None
        self.minus_buy_rect = None
        self.max_buy_rect = None
        self.plus_sell_rect = None
        self.minus_sell_rect = None
        self.max_sell_rect = None

        # cooldowns
        self.button_cooldowns = {
            "buy": 0, "plus_buy": 0, "minus_buy": 0, "max_buy": 0,
            "sell": 0, "plus_sell": 0, "minus_sell": 0, "max_sell": 0
        }

        # UI rect caches
        self.sidebar_rects = None
        self.ticker_rects = None
        self.portfolio_rects = {}
        self.visualize_rects = {}

    # ------------------------------------------------
    # SCREEN CONTROL
    # ------------------------------------------------
    def switch(self, screen_name):
        self.current_screen = screen_name

    def is_screen(self, name):
        return self.current_screen == name

    # ------------------------------------------------
    # For GUI to tell UIManager what rects exist
    # ------------------------------------------------
    def register_info_panel_rects(self, info):
        self.toggle_volume_rect = info.get("toggle_volume")
        self.toggle_candles_rect = info.get("toggle_candles")

        self.plus_buy_rect = info.get("plus_buy")
        self.minus_buy_rect = info.get("minus_buy")
        self.max_buy_rect = info.get("max_buy")
        self.buy_button_rect = info.get("buy")

        self.plus_sell_rect = info.get("plus_sell")
        self.minus_sell_rect = info.get("minus_sell")
        self.max_sell_rect = info.get("max_sell")
        self.sell_button_rect = info.get("sell")

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

        # ESC → pause menu
        if event.key == pygame.K_ESCAPE:
            choice = self.state.gui.render_pause_menu(screen, header_font, self.state)
            if choice == "quit":
                self.state.autosave()
                return "quit"
            elif choice == "toggle_crt":
                self.crt_enabled = not self.crt_enabled

        # Debug breakpoint triggers
        if event.key == pygame.K_b and self.selected_stock:
            d = self.state.tickers_obj[self.selected_stock]
            if len(d.recent_prices) < 30:
                d.recent_prices = [d.current_price * 0.9] * 30
            recent_high = max(d.recent_prices[-30:])
            d.current_price = recent_high * 1.05
            print("=== FORCED BREAKOUT ===")

        if event.key == pygame.K_KP0 and self.selected_stock:
            d = self.state.tickers_obj[self.selected_stock]
            if d.recent_prices:
                low = min(d.recent_prices[-30:])
                forced = low * 0.90
                d.current_price = forced
                d.last_price = forced
                d.recent_prices.append(forced)
                d.recent_prices = d.recent_prices[-200:]
                print("=== FORCED BREAKDOWN ===")

        # chart panning
        if event.key == pygame.K_LEFT:
            self.state.chart_offset -= 5
        if event.key == pygame.K_RIGHT:
            self.state.chart_offset += 5

        return None

    # ------------------------------------------------
    # MOUSE HANDLING
    # ------------------------------------------------
    def handle_mouse(self, mx, my, sidebar_data, click_zones):
        state = self.state
        print("HANDLE_MOUSE called with:", mx, my)

        # ============================================
        # PORTFOLIO SCREEN
        # ============================================
        if self.is_screen("portfolio"):

            # BACK
            if self.portfolio_rects.get("back") and self.portfolio_rects["back"].collidepoint(mx, my):
                self.switch("normal")
                return

            # VISUALIZE
            if self.portfolio_rects.get("visualize") and self.portfolio_rects["visualize"].collidepoint(mx, my):
                self.switch("visualize")
                return

            # Click stock
            for stk, rect in self.portfolio_rects.items():
                if stk in state.tickers and rect.collidepoint(mx, my):
                    self.selected_stock = stk
                    self.state.selected_stock = stk     # <<< REQUIRED
                    self.switch("normal")
                    return
            return

        # ============================================
        # VISUALIZE SCREEN
        # ============================================
        if self.is_screen("visualize"):
            if self.visualize_rects.get("back") and self.visualize_rects["back"].collidepoint(mx, my):
                self.switch("portfolio")
            return

        # ============================================
        # SIDEBAR BUTTONS
        # ============================================
        if self.sidebar_rects:
            for b in self.sidebar_rects:
                if b["rect"].collidepoint(mx, my):

                    if b["action"] == "view_portfolio":
                        self.switch("portfolio")
                    elif b["action"] == "open_shop":
                        print("Shop")
                    elif b["action"] == "view_analysis":
                        print("Analysis")

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

                    self.selected_stock = stk
                    self.state.selected_stock = stk     # <<< REQUIRED

                    if stk not in state.portfolio:
                        state.portfolio[stk] = {"shares": 0, "bought_at": [], "sell_qty": 0}
                    else:
                        state.portfolio[stk]["sell_qty"] = 0

                    try: state.sounds["chart"].play()
                    except: pass

                    return

        # ============================================
        # BUY / SELL BUTTONS
        # ============================================
        s = self.selected_stock
        if s:

            # ----- BUY PLUS -----
            if self.plus_buy_rect and self.plus_buy_rect.collidepoint(mx, my):
                self.button_cooldowns["plus_buy"] = 0.08
                state.tickers_obj[s].buy_qty += 1
                try: state.sounds["tick_up"].play()
                except: pass
                return

            # ----- BUY MINUS -----
            if self.minus_buy_rect and self.minus_buy_rect.collidepoint(mx, my):
                self.button_cooldowns["minus_buy"] = 0.08
                if state.tickers_obj[s].buy_qty > 0:
                    state.tickers_obj[s].buy_qty -= 1
                    try: state.sounds["tick_down"].play()
                    except: pass
                return

            # ----- MAX BUY -----
            if self.max_buy_rect and self.max_buy_rect.collidepoint(mx, my):
                self.button_cooldowns["max_buy"] = 0.08
                cash = state.account["money"]
                price = state.tickers_obj[s].current_price
                state.tickers_obj[s].buy_qty = int(cash // price)
                return

            # ----- BUY -----
            if self.buy_button_rect and self.buy_button_rect.collidepoint(mx, my):
                qty = state.tickers_obj[s].buy_qty
                if state.is_market_open and qty > 0:
                    before = state.portfolio[s]["shares"]
                    state.portfolio_mgr.buy_stock(s, qty)
                    if state.portfolio[s]["shares"] > before:
                        try: state.sounds["buy"].play()
                        except: pass
                self.button_cooldowns["buy"] = 0.08
                return

            # ----- SELL -----
            if self.sell_button_rect and self.sell_button_rect.collidepoint(mx, my):
                qty = state.portfolio[s]["sell_qty"]
                if state.is_market_open and qty > 0:
                    state.portfolio_mgr.sell_stock(s, qty)
                    try: state.sounds["sell"].play()
                    except: pass
                self.button_cooldowns["sell"] = 0.10
                return

            # ----- SELL MINUS -----
            if self.minus_sell_rect and self.minus_sell_rect.collidepoint(mx, my):
                self.button_cooldowns["minus_sell"] = 0.10
                if state.portfolio[s]["sell_qty"] > 0:
                    state.portfolio[s]["sell_qty"] -= 1
                    try: state.sounds["tick_down"].play()
                    except: pass
                return

            # ----- SELL PLUS -----
            if self.plus_sell_rect and self.plus_sell_rect.collidepoint(mx, my):
                self.button_cooldowns["plus_sell"] = 0.10
                if state.portfolio[s]["sell_qty"] < state.portfolio[s]["shares"]:
                    state.portfolio[s]["sell_qty"] += 1
                    try: state.sounds["tick_up"].play()
                    except: pass
                return

            # ----- MAX SELL -----
            if self.max_sell_rect and self.max_sell_rect.collidepoint(mx, my):
                self.button_cooldowns["max_sell"] = 0.10
                state.portfolio[s]["sell_qty"] = state.portfolio[s]["shares"]
                return

        # ============================================
        # NEWS TICKER
        # ============================================
        news = self.state.news
        if hasattr(news, "ticker_bar_rect") and news.ticker_bar_rect.collidepoint(mx, my):
            hit = news.handle_click(mx, my)
            if hit:
                self.selected_stock = hit
                self.state.selected_stock = hit     # <<< REQUIRED

                if hit not in state.portfolio:
                    state.portfolio[hit] = {"shares": 0, "bought_at": [], "sell_qty": 0}
                else:
                    state.portfolio[hit]["sell_qty"] = 0

                try: state.sounds["chart"].play()
                except: pass

                return
