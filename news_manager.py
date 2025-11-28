import pygame

import pygame

class NewsManager:
    def __init__(self, font):
        self.font = font

        # All current news events: each entry is {"text": str, "color": (r,g,b)}
        self.messages = []

        # Pixel offset for scrolling ticker
        self.scroll_offset = 1920

        # Speed at which ticker scrolls (pixels / second)
        self.scroll_speed = 160

        # Height of news bar
        self.bar_height = 60

        # Runtime-assigned each frame
        self.click_zones = {}         # { message_text : rect }
        self.ticker_bar_rect = None   # Rect of news bar

    # ---------------------------------------------------------
    # Add a news message to the queue
    # ---------------------------------------------------------
    def add_message(self, text, color=(255, 255, 255)):
        self.messages.append({"text": text, "color": color})

    # ---------------------------------------------------------
    # Clear all news messages
    # ---------------------------------------------------------
    def clear_messages(self):
        self.messages.clear()

    # ---------------------------------------------------------
    # Draw ticker + update scroll position
    # ---------------------------------------------------------
    def update_and_draw(self, screen, dt):
        screen_width, screen_height = screen.get_size()

        # Bar rectangle
        self.ticker_bar_rect = pygame.Rect(
            0,
            screen_height - self.bar_height,
            screen_width,
            self.bar_height
        )

        # Draw background bar
        pygame.draw.rect(screen, (104, 104, 104), self.ticker_bar_rect)

        # No messages → nothing to scroll
        if not self.messages:
            self.click_zones = {}
            return self.scroll_offset, {}, self.ticker_bar_rect

        # Clickable zones for each message
        self.click_zones = {}

        # Separator between messages
        separator_text = "   |   "
        separator_surface = self.font.render(separator_text, True, (230, 230, 230))

        # Pre-render all message surfaces
        rendered_segments = []
        for message in self.messages:
            text_surface = self.font.render(message["text"], True, message["color"])
            rendered_segments.append((text_surface, message))
            rendered_segments.append((separator_surface, None))

        # Draw position
        x_pos = self.scroll_offset
        y_pos = self.ticker_bar_rect.y + (self.bar_height // 2 - rendered_segments[0][0].get_height() // 2)

        # Draw each segment
        for surface, msg_data in rendered_segments:
            width = surface.get_width()

            # Draw text
            screen.blit(surface, (int(x_pos), y_pos))

            # If real message → create click zone
            if msg_data is not None:
                self.click_zones[msg_data["text"]] = pygame.Rect(
                    int(x_pos),
                    self.ticker_bar_rect.y,
                    width,
                    self.bar_height
                )

            x_pos += width

        total_scroll_width = x_pos - self.scroll_offset

        # Move left
        self.scroll_offset -= self.scroll_speed * dt

        # If the first item fully leaves the screen, remove it
        first_segment_width = rendered_segments[0][0].get_width()
        if self.scroll_offset < -first_segment_width:
            self.messages.pop(0)
            self.scroll_offset += first_segment_width  # maintain alignment

        # Loop back to the right if everything scrolled off
        if self.scroll_offset <= -total_scroll_width:
            self.scroll_offset = screen_width

        return self.scroll_offset, self.click_zones, self.ticker_bar_rect

    # ---------------------------------------------------------
    # Check if user clicked a message
    # ---------------------------------------------------------
    def handle_click(self, mouse_x, mouse_y):
        if not self.click_zones:
            return None

        for text, rect in self.click_zones.items():
            if rect.collidepoint(mouse_x, mouse_y):
                # Symbol is first token ("AAPL breaks resistance!")
                return text.split()[0]

        return None
