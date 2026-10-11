# trading_ai/real_time/backtesting/backtester.py

import pandas as pd
import numpy as np
from binance.client import Client
from trading_ai.real_time.strategy_factory import get_strategy


class Backtester:

    def __init__(self, api_key, api_secret, symbol, interval, leverage=1):
        self.client = Client(api_key, api_secret)
        self.symbol = symbol
        self.interval = interval
        self.leverage = leverage
        self.strategy = get_strategy("ema")
        self.trades = []
        
        # Professional: Transaction costs
        self.taker_fee = 0.0004  # Binance taker fee 0.04%
        self.maker_fee = 0.0002  # Binance maker fee 0.02%
        self.slippage = 0.0005   # Estimated slippage 0.05%
        self.funding_fee_per_trade = 0.0001  # Funding fee estimate

    # ============================================
    # FETCH HISTORICAL DATA
    # ============================================
    def fetch_data(self, start_str="30 days ago UTC"):
        klines = self.client.get_historical_klines(
            self.symbol,
            self.interval,
            start_str
        )

        df = pd.DataFrame(klines, columns=[
            "time","open","high","low","close","volume",
            "_","_","_","_","_","_"
        ])

        df["close"] = df["close"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)

        return df

    # ============================================
    # RUN BACKTEST
    # ============================================
    def run(self, df, sl_percent=0.003, tp_percent=0.006):

        position = None
        entry_price = 0

        for i in range(50, len(df)):

            window = df.iloc[:i]

            signal, price, confidence = self.strategy.generate_signal_from_df(window)

            if position is None and signal:
                position = signal
                entry_price = price

                if signal == "LONG":
                    sl = entry_price * (1 - sl_percent)
                    tp = entry_price * (1 + tp_percent)
                else:
                    sl = entry_price * (1 + sl_percent)
                    tp = entry_price * (1 - tp_percent)

                continue

            if position:

                current_high = df.iloc[i]["high"]
                current_low = df.iloc[i]["low"]

                exit_price = None

                if position == "LONG":
                    if current_low <= sl:
                        exit_price = sl
                    elif current_high >= tp:
                        exit_price = tp

                if position == "SHORT":
                    if current_high >= sl:
                        exit_price = sl
                    elif current_low <= tp:
                        exit_price = tp

                if exit_price:
                    # Professional: Calculate P&L with transaction costs
                    gross_pnl = (exit_price - entry_price) if position == "LONG" else (entry_price - exit_price)
                    gross_pnl *= self.leverage
                    
                    # Deduct transaction costs
                    entry_cost = entry_price * (self.taker_fee + self.slippage) * self.leverage
                    exit_cost = exit_price * (self.taker_fee + self.slippage) * self.leverage
                    funding_cost = entry_price * self.funding_fee_per_trade
                    
                    total_costs = entry_cost + exit_cost + funding_cost
                    net_pnl = gross_pnl - total_costs

                    self.trades.append({
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "gross_pnl": gross_pnl,
                        "costs": total_costs,
                        "net_pnl": net_pnl,
                        "position": position
                    })

                    position = None

        return self.calculate_statistics()

    # ============================================
    # STATS
    # ============================================
    def calculate_statistics(self):

        if not self.trades:
            return {}

        total_trades = len(self.trades)
        
        # Professional: Handle dict format with transaction costs
        if isinstance(self.trades[0], dict):
            net_pnls = [t["net_pnl"] for t in self.trades]
            gross_pnls = [t["gross_pnl"] for t in self.trades]
            costs = [t["costs"] for t in self.trades]
            wins = len([p for p in net_pnls if p > 0])
        else:
            net_pnls = self.trades
            wins = len([t for t in self.trades if t > 0])
        
        losses = total_trades - wins
        total_net_pnl = sum(net_pnls)
        
        if isinstance(self.trades[0], dict):
            total_gross_pnl = sum(gross_pnls)
            total_costs = sum(costs)
        else:
            total_gross_pnl = total_net_pnl
            total_costs = 0

        win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0

        returns = np.array(net_pnls)
        sharpe = np.mean(returns) / (np.std(returns) + 1e-9) if np.std(returns) > 0 else 0

        return {
            "total_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "win_rate": round(win_rate, 2),
            "gross_pnl": round(total_gross_pnl, 4),
            "transaction_costs": round(total_costs, 4),
            "net_pnl": round(total_net_pnl, 4),
            "sharpe_ratio": round(sharpe, 4),
            "avg_cost_per_trade": round(total_costs / total_trades, 6) if total_trades > 0 else 0
        }