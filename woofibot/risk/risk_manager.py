from typing import Dict
from ..core.portfolio import Portfolio


import time
from math import isfinite

class RiskManager:
    def __init__(self, portfolio: Portfolio, config):
        self.pf = portfolio
        self.cfg = config
        self.start_equity = portfolio.cash_usd

    def can_trade(self, prices: Dict[str, float], order_notional: float = 0.0) -> bool:
        # daily loss limit check
        eq = self.pf.equity(prices)
        dd_pct = (self.start_equity - eq) / max(1e-9, self.start_equity) * 100
        # max exposure check
        exposure = self.pf.open_notional(prices)
        # Prevent opening if resulting exposure would breach cap
        if exposure + order_notional > self.cfg.max_exposure_usd:
            return False
        if dd_pct >= self.cfg.daily_loss_limit_pct:
            return False
        return True

    def check_auto_close(self, prices: Dict[str, float]):
        """Return a close-order dict when TP/SL conditions met, else None."""
        # iterate through open positions (support multi-symbol)
        for sym, pos in self.pf.positions.items():
            if pos.qty == 0:
                continue
            mark = prices.get(sym)
            if mark is None or not isfinite(mark):
                continue
            entry = pos.avg_price or mark
            unreal_pct = (mark - entry) / entry * 100 if pos.qty > 0 else (entry - mark) / entry * 100
            # TP/SL percentages are positive numbers in config
            if unreal_pct >= self.cfg.take_profit_pct:
                side = "sell" if pos.qty > 0 else "buy"
                qty_quote = abs(pos.qty) * mark
                return {"symbol": sym, "side": side, "qty_quote": qty_quote, "reason": "tp"}
            if unreal_pct <= -self.cfg.stop_loss_pct:
                side = "sell" if pos.qty > 0 else "buy"
                qty_quote = abs(pos.qty) * mark
                return {"symbol": sym, "side": side, "qty_quote": qty_quote, "reason": "sl"}
        return None
