# TraderSim

A retro-styled stock market trading simulator built with Python and Pygame. Manage a virtual portfolio, analyze candlestick charts, and trade stocks in a simulated market with realistic price dynamics.

![Python](https://img.shields.io/badge/Python-3.x-blue) ![Pygame](https://img.shields.io/badge/Pygame-2.x-green) ![SQLite](https://img.shields.io/badge/Database-SQLite-lightgrey)

---

## Features

- **Realistic Market Simulation** — Price engine with mean reversion, momentum, volatility, order flow impact, sector sentiment, and market mood
- **Market Hours** — Trades only execute during market hours (9:30 AM – 4:00 PM in-game time)
- **Trading Mechanics** — Market orders and limit orders with cost-basis tracking
- **Interactive Charts** — Zoomable, pannable candlestick (OHLC) and volume charts
- **Portfolio Management** — Track holdings, cost basis, and portfolio value in real time
- **News Ticker** — Scrolling news feed at the bottom of the screen
- **Retro UI** — CRT pixelation effect toggle, VCR-style monospace font, and retro aesthetics
- **Persistence** — SQLite database and JSON config files save your progress automatically

---

## Screenshots

> *(Add screenshots here)*

---

## Getting Started

### Prerequisites

- Python 3.x
- Pygame

```bash
pip install pygame
```

### Running the App

```bash
python main.py
```

---

## Project Structure

```
TraderSim/
├── main.py                 # Main game loop and state management
├── gui.py                  # All UI rendering (Pygame)
├── gamestate.py            # Core game logic
├── UiEventManager.py       # UI state and event handling
├── stock.py                # Stock class (price, history, properties)
├── portfolio_manager.py    # Buy/sell operations
├── candle_manager.py       # OHLC candle data management
├── news_manager.py         # News ticker system
├── helper_functions.py     # Market simulation logic and utilities
├── database.py             # Database connection
├── database_setup.py       # DB schema initialization
├── game/
│   └── tickers.json        # Stock metadata (30+ stocks)
├── player/
│   ├── account.json        # Player account state
│   └── portfolio.json      # Player holdings
└── assets/
    ├── buttons/            # UI button images
    ├── fonts/              # VCR OSD Mono font
    ├── sounds/             # Audio effects
    └── overlays/           # CRT screen overlay
```

---

## How It Works

### Market Simulation

Each price tick is computed from several layered forces:

| Force | Description |
|---|---|
| Mean Reversion | Pulls price back toward a baseline ("gravity") |
| Momentum | Carries recent price trends forward |
| Volatility | Random noise scaled per-stock |
| Order Flow | Recent buy/sell activity impacts price |
| Sector Sentiment | Sector-wide mood shifts affect correlated stocks |
| Market Mood | Global market-wide sentiment modifier |

Micro-price sampling between ticks produces realistic OHLC candle data.

### Trading

- **Market Orders** — Execute immediately at the current price during market hours
- **Limit Orders** — Queue at a target price and fill automatically when the market reaches it
- **Portfolio Tracking** — Cost basis is tracked per stock for P&L calculations

---

## Controls

| Action | Input |
|---|---|
| Select stock | Click ticker in list |
| Open buy/sell panel | Click Buy / Sell button |
| Zoom chart | Scroll wheel on chart |
| Pan chart | Click and drag |
| Toggle CRT effect | *(in-game button)* |

---

## Data Persistence

TraderSim uses **SQLite** (`game.db`) and **JSON** files to persist state:

- `tickers` — Stock metadata and current prices
- `candles` — Full OHLC history per stock (capped at 2,000 candles in RAM)
- `portfolio` — Current holdings and cost basis
- `account` — Cash balance and market time
- `news` — Historical news messages

---

## License

This project is for personal/educational use. No license applied.
