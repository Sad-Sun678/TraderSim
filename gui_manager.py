# ============================================================
# gui_manager.py — ALL UI, ALL RENDERING, NO GAME LOGIC
# ============================================================
import pygame
import sys


class GUIManager:
    def __init__(self, state):
        pygame.init()

        self.state = state

        # -----------------------------
        # SCREEN & FONTS
        # -----------------------------
        self.screen_width = 1600
        self.screen_height = 900
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("TraderSim")

        # Load fonts (placeholder – real ones will be moved from gui.py)
        self.font_small = pygame.font.SysFont("consolas", 16)
        self.font_med = pygame.font.SysFont("consolas", 20)
        self.font_large = pygame.font.SysFont("consolas", 28)

        # -----------------------------
        # UI STATE (WILL BE FILLED NEXT)
        # -----------------------------
        self.mouse_x = 0
        self.mouse_y = 0

        self.click_zones = {}
        self.button_rects = {}

        # CHART settings (from GUI, not GameState)
        self.chart_x = 380
        self.chart_y = 350
        self.chart_w = 850
        self.chart_h = 300

        # Anything from gui.py that is UI will move into here next

    # ===========================================================
    # EVENT LOOP
    # ===========================================================
    def handle_events(self):
        """Capture mouse/keyboard events and update GUI or GameState."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # More event handling (clicks, drags, scroll) will go here
            # AFTER we migrate gui.py functions.

    # ===========================================================
    # RENDER LOOP
    # ===========================================================
    def render(self):
        """Draw every UI element each frame."""
        self.screen.fill((5, 0, 10))

        # These will be replaced by real migrated versions from gui.py:
        # self.render_ticker_list()
        # self.render_chart()
        # self.render_info_panel()
        self.render_header()
        # self.render_sidebar()

        pygame.display.flip()

    # -----------------------------------------------------------
    # PLACEHOLDER FUNCTIONS (will be overwritten with migrants)
    # -----------------------------------------------------------
    def render_header(self):
        """Draws the top header bar (money, selected stock, day/time)."""

        state = self.state
        scr = self.screen

        # HEADER BAR BACKGROUND
        pygame.draw.rect(scr, (20, 0, 40), (0, 0, self.screen_width, 60))

        # MONEY DISPLAY
        money_txt = self.font_large.render(f"${state.account['money']:,.2f}", True, (255, 255, 255))
        scr.blit(money_txt, (20, 15))

        # SELECTED STOCK DISPLAY
        if state.selected_stock:
            stock_name = state.selected_stock
            data = state.tickers[stock_name]

            stock_txt = self.font_med.render(
                f"{stock_name}  ${data['current_price']:.2f}",
                True,
                (180, 220, 255)
            )
            scr.blit(stock_txt, (260, 20))

        # GAME DAY & TIME
        day_txt = self.font_med.render(f"Day {state.market_day}", True, (255, 255, 0))
        time_txt = self.font_med.render(f"{state.market_time:04d}", True, (200, 200, 200))

        scr.blit(day_txt, (520, 10))
        scr.blit(time_txt, (520, 32))

    def render_ticker_list(self):
        pass

    def render_chart(self):
        pass

    def render_info_panel(self):
        pass

    def render_sidebar(self):
        pass
