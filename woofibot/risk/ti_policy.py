import time
from typing import Dict, Any
from ..core.portfolio import Portfolio
from ..utils.config import TIConfig


class TIPolicy:
    def __init__(self, cfg: TIConfig):
        self.cfg = cfg
        self._last_trade_ts: Dict[str, float] = {}

    def allow_signal(self, od: Dict[str, Any], pf: Portfolio, prices: Dict[str, float]) -> bool:
        sym = od.get("symbol")
        side = od.get("side")
        qty_quote = float(od.get("qty_quote", 0.0))
        if qty_quote < self.cfg.min_order_notional:
            return False
        now = time.time()
        lt = self._last_trade_ts.get(sym, 0.0)
        if now - lt < self.cfg.min_trade_interval_sec:
            return False
        pos = pf.positions.get(sym)
        if pos and pos.qty != 0:
            if pos.ts and now - pos.ts < self.cfg.min_hold_time_sec:
                if (pos.qty > 0 and side == "sell") or (pos.qty < 0 and side == "buy"):
                    return False
        return True

    def record_fill(self, symbol: str):
        self._last_trade_ts[symbol] = time.time()
