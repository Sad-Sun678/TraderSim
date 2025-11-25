# import sqlite3
#
# conn = sqlite3.connect("game.db")
# cur = conn.cursor()
#
# cur.execute("DELETE FROM tickers;")
# cur.execute("DELETE FROM candles;")
# cur.execute("DELETE FROM portfolio;")
# cur.execute("DELETE FROM news;")
# cur.execute("DELETE FROM account;")
#
# # Reinsert the one account row
# cur.execute("""
#     INSERT INTO account (id, money, market_time, market_open, market_close, market_day)
#     VALUES (1, 150000, 570, 570, 960, 1)
# """)
#
# conn.commit()
# conn.close()
#
# print("DB wiped clean.")

##################
#CLEARS DB
##################


import json
import sqlite3

# -------------------------------------------------
# 1. This is already a Python dict — DO NOT json.loads it
# -------------------------------------------------
TICKERS = {
    "SOLR": {
        "ticker": "SOLR",
        "name": "Solara Energy Corp",
        "sector": "Energy",
        "current_price": 41.61,
        "last_price": 41.61,
        "base_price": 40.0,
        "volatility": "medium",
        "gravity": 0.0003,
        "trend": 0,
        "ath": 41.61,
        "atl": 41.61,
        "buy_qty": 0,
        "volume": 22000,
        "avg_volume": 20000
    },
    "NEOT": {
        "ticker": "NEOT",
        "name": "Neoteric Tech Holdings",
        "sector": "Technology",
        "current_price": 132.40,
        "last_price": 132.40,
        "base_price": 120.0,
        "volatility": "high",
        "gravity": 0.0002,
        "trend": 0,
        "ath": 132.40,
        "atl": 132.40,
        "buy_qty": 0,
        "volume": 58000,
        "avg_volume": 55000,
        "volume_history": [],
        "history": [],
        "day_history": []
    },
    "GLBX": {
        "ticker": "GLBX",
        "name": "Globetronix Robotics",
        "sector": "Technology",
        "current_price": 88.20,
        "last_price": 88.20,
        "base_price": 85.0,
        "volatility": "high",
        "gravity": 0.0004,
        "trend": 0,
        "ath": 88.20,
        "atl": 88.20,
        "buy_qty": 0,
        "volume": 31000,
        "avg_volume": 30000,
        "volume_history": [],
        "history": [],
        "day_history": []
    },
    "FNLT": {
        "ticker": "FNLT",
        "name": "Finality Financial Group",
        "sector": "Finance",
        "current_price": 58.75,
        "last_price": 58.75,
        "base_price": 55.0,
        "volatility": "low",
        "gravity": 0.0002,
        "trend": 0,
        "ath": 58.75,
        "atl": 58.75,
        "buy_qty": 0,
        "volume": 18000,
        "avg_volume": 19000,
        "volume_history": [],
        "history": [],
        "day_history": []
    },
    "AQUA": {
        "ticker": "AQUA",
        "name": "Aquadyne Water Systems",
        "sector": "Utilities",
        "current_price": 27.44,
        "last_price": 27.44,
        "base_price": 28.0,
        "volatility": "low",
        "gravity": 0.0001,
        "trend": 0,
        "ath": 27.44,
        "atl": 27.44,
        "buy_qty": 0,
        "volume": 12000,
        "avg_volume": 10000,
        "volume_history": [],
        "history": [],
        "day_history": []
    },
    "BRIX": {
        "ticker": "BRIX",
        "name": "Brixon Construction Co",
        "sector": "Industrial",
        "current_price": 73.55,
        "last_price": 73.55,
        "base_price": 70.0,
        "volatility": "medium",
        "gravity": 0.0003,
        "trend": 0,
        "ath": 73.55,
        "atl": 73.55,
        "buy_qty": 0,
        "volume": 25000,
        "avg_volume": 24000,
        "volume_history": [],
        "history": [],
        "day_history": []
    },
    "CRSN": {
        "ticker": "CRSN",
        "name": "Crescent Pharmaceuticals",
        "sector": "Healthcare",
        "current_price": 94.28,
        "last_price": 94.28,
        "base_price": 92.0,
        "volatility": "medium",
        "gravity": 0.0002,
        "trend": 0,
        "ath": 94.28,
        "atl": 94.28,
        "buy_qty": 0,
        "volume": 32000,
        "avg_volume": 30000,
        "volume_history": [],
        "history": [],
        "day_history": []
    },
    "GRNV": {
        "ticker": "GRNV",
        "name": "Green Valley Foods",
        "sector": "Consumer",
        "current_price": 19.14,
        "last_price": 19.14,
        "base_price": 20.0,
        "volatility": "low",
        "gravity": 0.0004,
        "trend": 0,
        "ath": 19.14,
        "atl": 19.14,
        "buy_qty": 0,
        "volume": 8000,
        "avg_volume": 10000,
        "volume_history": [],
        "history": [],
        "day_history": []
    },
    "ALTO": {
        "ticker": "ALTO",
        "name": "Alto AeroDynamics",
        "sector": "Industrial",
        "current_price": 148.90,
        "last_price": 148.90,
        "base_price": 140.0,
        "volatility": "high",
        "gravity": 0.0003,
        "trend": 0,
        "ath": 148.90,
        "atl": 148.90,
        "buy_qty": 0,
        "volume": 54000,
        "avg_volume": 50000,
        "volume_history": [],
        "history": [],
        "day_history": []
    },
    "MSTR": {
        "ticker": "MSTR",
        "name": "Maestro Media LLC",
        "sector": "Communication",
        "current_price": 44.02,
        "last_price": 44.02,
        "base_price": 45.0,
        "volatility": "medium",
        "gravity": 0.0003,
        "trend": 0,
        "ath": 44.02,
        "atl": 44.02,
        "buy_qty": 0,
        "volume": 22000,
        "avg_volume": 21000,
        "volume_history": [],
        "history": [],
        "day_history": []
    },

    "STGW": {
        "ticker": "STGW",
        "name": "Stargrow Agriculture",
        "sector": "Consumer",
        "current_price": 12.73,
        "last_price": 12.73,
        "base_price": 13.5,
        "volatility": "medium",
        "gravity": 0.0005,
        "trend": 0,
        "ath": 12.73,
        "atl": 12.73,
        "buy_qty": 0,
        "volume": 6000,
        "avg_volume": 9000,
        "volume_history": [],
        "history": [],
        "day_history": []
    },

    "VRSE": {
        "ticker": "VRSE",
        "name": "VersEdge Software",
        "sector": "Technology",
        "current_price": 66.88,
        "last_price": 66.88,
        "base_price": 60.0,
        "volatility": "high",
        "gravity": 0.0002,
        "trend": 0,
        "ath": 66.88,
        "atl": 66.88,
        "buy_qty": 0,
        "volume": 40000,
        "avg_volume": 35000,
        "volume_history": [],
        "history": [],
        "day_history": []
    },

    "IRON": {
        "ticker": "IRON",
        "name": "Ironshield Defense Corp",
        "sector": "Industrial",
        "current_price": 103.22,
        "last_price": 103.22,
        "base_price": 100.0,
        "volatility": "medium",
        "gravity": 0.0003,
        "trend": 0,
        "ath": 103.22,
        "atl": 103.22,
        "buy_qty": 0,
        "volume": 31000,
        "avg_volume": 30000,
        "volume_history": [],
        "history": [],
        "day_history": []
    },

    "CTRP": {
        "ticker": "CTRP",
        "name": "Centropoint Retail",
        "sector": "Consumer",
        "current_price": 8.44,
        "last_price": 8.44,
        "base_price": 9.0,
        "volatility": "low",
        "gravity": 0.0004,
        "trend": 0,
        "ath": 8.44,
        "atl": 8.44,
        "buy_qty": 0,
        "volume": 9000,
        "avg_volume": 10000,
        "volume_history": [],
        "history": [],
        "day_history": []
    },

    "HRTX": {
        "ticker": "HRTX",
        "name": "Horizon Textiles",
        "sector": "Industrial",
        "current_price": 51.19,
        "last_price": 51.19,
        "base_price": 50.0,
        "volatility": "medium",
        "gravity": 0.0003,
        "trend": 0,
        "ath": 51.19,
        "atl": 51.19,
        "buy_qty": 0,
        "volume": 15000,
        "avg_volume": 17000,
        "volume_history": [],
        "history": [],
        "day_history": []
    },

    "OMNI": {
        "ticker": "OMNI",
        "name": "Omnitech Global",
        "sector": "Technology",
        "current_price": 254.90,
        "last_price": 254.90,
        "base_price": 240.0,
        "volatility": "high",
        "gravity": 0.0002,
        "trend": 0,
        "ath": 254.90,
        "atl": 254.90,
        "buy_qty": 0,
        "volume": 68000,
        "avg_volume": 65000,
        "volume_history": [],
        "history": [],
        "day_history": []
    },

    "MEGA": {
        "ticker": "MEGA",
        "name": "MegaMart Holdings",
        "sector": "Consumer",
        "current_price": 34.77,
        "last_price": 34.77,
        "base_price": 33.0,
        "volatility": "low",
        "gravity": 0.0003,
        "trend": 0,
        "ath": 34.77,
        "atl": 34.77,
        "buy_qty": 0,
        "volume": 20000,
        "avg_volume": 21000,
        "volume_history": [],
        "history": [],
        "day_history": []
    },

    "QUAN": {
        "ticker": "QUAN",
        "name": "Quantum Analytics",
        "sector": "Technology",
        "current_price": 177.44,
        "last_price": 177.44,
        "base_price": 165.0,
        "volatility": "high",
        "gravity": 0.0003,
        "trend": 0,
        "ath": 177.44,
        "atl": 177.44,
        "buy_qty": 0,
        "volume": 52000,
        "avg_volume": 50000,
        "volume_history": [],
        "history": [],
        "day_history": []
    },

    "VSPR": {
        "ticker": "VSPR",
        "name": "Vesper Renewable Power",
        "sector": "Energy",
        "current_price": 29.33,
        "last_price": 29.33,
        "base_price": 28.0,
        "volatility": "medium",
        "gravity": 0.0004,
        "trend": 0,
        "ath": 29.33,
        "atl": 29.33,
        "buy_qty": 0,
        "volume": 16000,
        "avg_volume": 15000,
        "volume_history": [],
        "history": [],
        "day_history": []
    }

}

# -------------------------------------------------
# 2. Connect to DB
# -------------------------------------------------
conn = sqlite3.connect("game.db")
cur = conn.cursor()

# -------------------------------------------------
# 3. Insert each ticker into DB
# -------------------------------------------------
for symbol, data in TICKERS.items():
    cur.execute("""
        INSERT OR REPLACE INTO tickers (
            ticker, name, sector, current_price, last_price,
            base_price, volatility, gravity, trend, ath, atl,
            buy_qty, volume, avg_volume
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["ticker"],
        data["name"],
        data["sector"],
        data["current_price"],
        data["last_price"],
        data["base_price"],
        data["volatility"],
        data["gravity"],
        data["trend"],
        data["ath"],
        data["atl"],
        data["buy_qty"],
        data["volume"],
        data["avg_volume"]
    ))

conn.commit()
conn.close()

print("Tickers inserted successfully!")
