class BacktestTradeManager:
    def __init__(self):
        self.active_trades = []  # ⬅️ Supports multiple concurrent trades
        self.trade_log = []
        self.total_trades = 0

    def enter_trade(self, direction, entry_price, sl, tp, time, index=None):
        trade = {
            "direction": direction,
            "entry_price": entry_price,
            "sl": sl,
            "tp": tp,
            "entry_time": time,
            "entry_index": index,
            "exit_price": None,
            "exit_time": None,
            "status": "open"
        }
        self.active_trades.append(trade)
        self.total_trades += 1

    def check_all_trades(self, candle):
        index = candle.name
        time = candle["time"]
        high = candle["high"]
        low = candle["low"]

        still_open = []
        for trade in self.active_trades:
            dir = trade["direction"]
            sl = trade["sl"]
            tp = trade["tp"]
            hit_tp = False
            hit_sl = False

            if dir == "buy":
                if low <= sl:
                    hit_sl = True
                elif high >= tp:
                    hit_tp = True
            elif dir == "sell":
                if high >= sl:
                    hit_sl = True
                elif low <= tp:
                    hit_tp = True

            if hit_tp or hit_sl:
                trade["status"] = "won" if hit_tp else "lost"
                trade["exit_price"] = tp if hit_tp else sl
                trade["exit_time"] = time
                self.trade_log.append(trade)
            else:
                still_open.append(trade)

        self.active_trades = still_open

    def get_results(self):
        wins = [t for t in self.trade_log if t["status"] == "won"]
        losses = [t for t in self.trade_log if t["status"] == "lost"]
        total = len(self.trade_log)
        pnl = 0

        for t in self.trade_log:
            reward = abs(t["tp"] - t["entry_price"])
            risk = abs(t["entry_price"] - t["sl"])
            if t["status"] == "won":
                pnl += reward
            elif t["status"] == "lost":
                pnl -= risk

        return {
            "total_trades": total,
            "wins": len(wins),
            "losses": len(losses),
            "expired": 0,  # Always 0 now
            "win_rate": round(len(wins) / total * 100, 2) if total > 0 else 0,
            "net_pnl": round(pnl, 5)
        }
