class PortfolioManager:
    def __init__(self, state):
        """
        Holds all portfolio data & logic.
        `state` is the GameState instance – used only for:
        - account money
        - tickers_obj for price lookup
        - DB connection during autosave
        """
        self.state = state
        self.portfolio = state.portfolio  # direct reference


    # --------------- VALUE CALCULATION ---------------
    def get_portfolio_value(self):
        total = 0
        for ticker, entry in self.portfolio.items():
            shares = entry["shares"]
            price = self.state.tickers_obj[ticker].current_price
            total += price * shares
        return total

    # --------------- BUY LOGIC ---------------
    def buy_stock(self, stock_name, amount=1):
        stock = self.state.tickers_obj[stock_name]
        price = stock.current_price
        cost = price * amount

        if self.state.account["money"] < cost:
            print("Not enough money!")
            return False

        # pay
        self.state.account["money"] -= cost

        # ensure exists
        if stock_name not in self.portfolio:
            self.portfolio[stock_name] = {"shares": 0, "bought_at": [], "sell_qty": 0}

        # add shares
        self.portfolio[stock_name]["shares"] += amount
        for _ in range(amount):
            self.portfolio[stock_name]["bought_at"].append(price)

        # bump recently_bought
        rb = self.state.recently_bought.setdefault(stock_name, {"order_force_time_delta": 0})
        rb["order_force_time_delta"] += amount

        print(f"Bought {amount} share(s) of {stock_name} @ {price:.2f}")
        return True

    # --------------- SELL LOGIC ---------------
    def sell_stock(self, stock_name, amount=1):
        if stock_name not in self.portfolio:
            print("No shares to sell!")
            return False

        if self.portfolio[stock_name]["shares"] < amount:
            print("Not enough shares to sell!")
            return False

        stock = self.state.tickers_obj[stock_name]
        price = stock.current_price

        # adjust holdings
        self.portfolio[stock_name]["shares"] -= amount
        self.state.account["money"] += price * amount

        # remove from cost basis
        for _ in range(amount):
            if self.portfolio[stock_name]["bought_at"]:
                self.portfolio[stock_name]["bought_at"].pop()

        print(f"Sold {amount} share(s) of {stock_name} @ {price:.2f}")
        return True
