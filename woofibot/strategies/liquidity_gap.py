from typing import List, Dict
from .base import StrategyBase


class LiquidityGapStrategy(StrategyBase):
    def on_tick(self, symbol_prices: Dict[str, float], exchange, risk_mgr) -> List[Dict]:
        orders = []
        min_spread_pct = float(self.params.get("min_spread_pct", 0.15))
        order_size = float(self.params.get("order_size_override", 0))
        for sym, px in symbol_prices.items():
            bid, ask = exchange.get_orderbook(sym)
            spread_pct = (ask - bid) / ((ask + bid) / 2) * 100 if ask and bid else 0
            if spread_pct >= min_spread_pct:
                size = order_size or exchange.portfolio.cash_usd * 0.01  # 1% equity if not provided
                orders.append({"symbol": sym, "side": "buy", "qty_quote": size})
        return orders
