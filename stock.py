import random, math

class Stock:
    def __init__(self, ticker, info):
        """
        info comes from DB and contains ONLY persistent fields.
        All runtime-only fields get initialized here.
        """
        self.ticker = ticker

        # -----------------------
        # PERSISTENT DB FIELDS
        # -----------------------
        self.name = info["name"]
        self.sector = info["sector"]

        self.current_price = info["current_price"]
        self.last_price = info["last_price"]
        self.base_price = info["base_price"]

        self.volatility = info["volatility"]
        self.gravity = info["gravity"]
        self.trend = info["trend"]

        self.ath = info["ath"]
        self.atl = info["atl"]

        self.buy_qty = info["buy_qty"]
        self.volume = info["volume"]
        self.avg_volume = info["avg_volume"]

        # volume cap optional / safe default
        self.volume_cap = info.get("volume_cap", self.avg_volume * 12)

        # -----------------------
        # RUNTIME-ONLY FIELDS
        # -----------------------
        self.history = []                       # legacy (not used much)
        self.volume_history = []                # per tick volume log
        self.recent_prices = []                 # rolling last X prices

        # OHLC candle history (7-day charts, etc.)
        self.day_history = info.get("day_history", [])

        # buffer for building each 5-minute candle
        self.ohlc_buffer = []

        # breakout cooldown
        self.last_breakout_time = info.get("last_breakout_time", -9999)

        # used by apply_tick
        self._open_tmp = None
        self.intraday_bias = None  # daily volume shaping factor
        self.daily_volume_phase = None  # shifts sinusoidal volume curve
        self.seasonal_bias = 0.0  # optional seasonal influence
    # =====================================================================
    # FULL TICK LOGIC REFACTORED FROM GAMESTATE TO HERE
    # =====================================================================
    def apply_tick(self, gs):
        """
        Full migrated tick logic (clean + non-duplicated).
        GameState only advances time and calls this.
        """

        # ----------------------------------------------------
        # PRICE + TREND
        # ----------------------------------------------------
        current_price = self.current_price
        previous_price = self.last_price
        self.last_price = current_price

        base = self.base_price

        # Momentum update
        price_diff = current_price - previous_price
        self.trend = self.trend * 0.9 + price_diff * 0.1
        momentum_force = self.trend * 0.01

        # ----------------------------------------------------
        # VOLATILITY MODEL
        # ----------------------------------------------------
        vol_map = {
            "low": (0.003, 0.015),
            "medium": (0.015, 0.06),
            "high": (0.04, 0.14)
        }
        sigma_min, sigma_max = vol_map[self.volatility]

        sigma_raw = random.uniform(sigma_min, sigma_max)

        vol_mult = max(0.75, min(3.0, self.volume / self.avg_volume))
        sigma = sigma_raw * vol_mult

        # ----------------------------------------------------
        # MEAN REVERSION
        # ----------------------------------------------------
        fair_value_force = (base - current_price) * (self.gravity * 1.3)

        # ----------------------------------------------------
        # ORDER PRESSURE
        # ----------------------------------------------------
        order_delta = gs.recently_bought[self.ticker]["order_force_time_delta"]
        order_delta *= 0.98
        gs.recently_bought[self.ticker]["order_force_time_delta"] = order_delta

        liquidity_factor = 1 / max(1.0, math.sqrt(self.avg_volume))
        order_force = order_delta * 0.000001 * liquidity_factor

        # ----------------------------------------------------
        # SECTOR SENTIMENT
        # ----------------------------------------------------
        sector_force = gs.sector_sentiment.get(self.sector, 0) * 0.003

        # ----------------------------------------------------
        # GLOBAL NOISE + MOOD
        # ----------------------------------------------------
        noise_force = random.gauss(0, 0.003 if gs.is_market_open else 0.0004)
        mood_force = gs.market_mood

        # ----------------------------------------------------
        # SEASONAL EFFECTS
        # ----------------------------------------------------
        profile = gs.season_profiles[gs.game_season]
        season_trend = profile["trend_bias"]
        sigma *= profile["volatility_mult"]

        # ----------------------------------------------------
        # FINAL PRICE MOVEMENT
        # ----------------------------------------------------
        change = (
                fair_value_force +
                momentum_force +
                random.gauss(0, sigma) +
                order_force +
                sector_force +
                noise_force +
                mood_force +
                season_trend
        )

        new_price = max(0.01, current_price + change)
        self.current_price = round(new_price, 2)

        # ----------------------------------------------------
        # BREAKOUT LOGIC (trend + volatility boost)
        # ----------------------------------------------------
        last_close = current_price
        cooldown = 120

        if gs.market_time - self.last_breakout_time >= cooldown and len(self.recent_prices) >= 20:
            window = self.recent_prices[-30:]
            recent_high = max(window)
            recent_low = min(window)

            breakout_up = last_close > recent_high * 1.01
            breakout_down = last_close < recent_low * 0.99

            if breakout_up:
                self.last_breakout_time = gs.market_time
                self.trend += last_close * 0.002
                sigma *= 1.5
                gs.news_messages.append({
                    "text": f"{self.ticker} breaks resistance! Bullish breakout!",
                    "color": (0, 255, 0)
                })

            elif breakout_down:
                self.last_breakout_time = gs.market_time
                self.trend -= last_close * 0.002
                sigma *= 1.6
                gs.news_messages.append({
                    "text": f"{self.ticker} breaks support! Bearish breakdown!",
                    "color": (255, 80, 80)
                })

        # store last_close into recent history
        self.recent_prices.append(last_close)
        self.recent_prices = self.recent_prices[-200:]

        # ----------------------------------------------------
        # VOLUME SIMULATION (clean, no duplicates)
        # ----------------------------------------------------
        base_vol = self.avg_volume
        vol = self.volume
        t = gs.market_time

        if gs.is_market_open:
            vol += (base_vol - vol) * 0.05
            vol += random.randint(-int(base_vol * 0.025), int(base_vol * 0.025))

            if self.intraday_bias is None:
                self.intraday_bias = random.uniform(0.7, 1.3)
            vol *= self.intraday_bias

            if self.daily_volume_phase is None or t < 5:
                self.daily_volume_phase = random.uniform(-0.7, 0.7)

            phase = self.daily_volume_phase
            t_ratio = (t - gs.market_open) / max(1, gs.market_close - gs.market_open)
            sin_wave = 1.0 + 0.25 * math.sin(6.28 * (t_ratio + phase))
            vol *= sin_wave

            if 570 <= t <= 615:
                vol *= random.uniform(1.2, 2.0)
            elif 720 <= t <= 810:
                vol *= random.uniform(0.7, 0.95)
            elif 900 <= t <= 960:
                vol *= random.uniform(1.1, 1.7)

            if random.random() < 0.02:
                vol *= random.uniform(1.3, 3.2)

        else:
            target_ah = base_vol * random.uniform(0.08, 0.18)
            vol += (target_ah - vol) * 0.15
            vol += random.randint(-int(base_vol * 0.005), int(base_vol * 0.005))

        # seasonal multiplier ONCE
        vol *= profile["volume_mult"]

        # adaptive cap growth
        if gs.is_market_open:
            if vol > self.volume_cap * 0.7:
                self.volume_cap *= random.uniform(1.01, 1.05)
            elif vol < self.volume_cap * 0.3:
                self.volume_cap *= random.uniform(0.97, 0.995)
            self.volume_cap *= random.uniform(0.999, 1.001)

        # safe clamp (protects agains SQLite overflow)
        self.volume_cap = max(base_vol * 5, min(self.volume_cap, base_vol * 40))

        # SOFT clamp instead of hard cap (looks natural)
        if vol > self.volume_cap:
            vol = self.volume_cap - (self.volume_cap - vol) * 0.3

        vol = max(150, vol)
        self.volume = int(vol)

        self.volume_history.append(self.volume)
        if len(self.volume_history) > 700:
            self.volume_history.pop(0)

        # ----------------------------------------------------
        # OHLC CANDLE (exact behavior)
        # ----------------------------------------------------
        opening_price = current_price
        micro_price = opening_price
        micro_prices = []

        for _ in range(5):
            micro_change = random.gauss(0, sigma * 0.4)
            micro_price = max(0.01, micro_price + micro_change)
            micro_prices.append(micro_price)

        self.ohlc_buffer.extend(micro_prices)
        self.ohlc_buffer.append(new_price)

        prices = self.ohlc_buffer

        entry = {
            "day": gs.game_day,
            "time": int(gs.market_time),
            "open": prices[0],
            "high": max(prices),
            "low": min(prices),
            "close": prices[-1],
            "volume": self.volume
        }

        self.day_history.append(entry)
        self.ohlc_buffer = []

        if len(self.day_history) > 2000:
            self.day_history.pop(0)
