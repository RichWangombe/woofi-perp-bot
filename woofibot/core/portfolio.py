from dataclasses import dataclass, field
from typing import Dict
import time


@dataclass
class Position:
    qty: float = 0.0  # base units
    avg_price: float = 0.0
    ts: float = 0.0  # timestamp of last open/increase


@dataclass
class Portfolio:
    cash_usd: float = 1000.0
    positions: Dict[str, Position] = field(default_factory=dict)
    realized_pnl_usd: float = 0.0
    _latest_prices: Dict[str, float] = field(default_factory=dict)

    def update_fill(self, symbol: str, side: str, qty_base: float, price: float, fee: float):
        pos = self.positions.get(symbol, Position())
        realized_delta = 0.0
        if side == "buy":
            # Cash outflow for buys
            self.cash_usd -= qty_base * price
            # If we are short, close part/all of it first
            if pos.qty < 0:
                close_qty = min(qty_base, -pos.qty)
                realized_delta += close_qty * (pos.avg_price - price)
                pos.qty += close_qty  # moves toward zero from negative
                qty_base -= close_qty
                if pos.qty == 0:
                    pos.avg_price = 0.0
            # Open/increase long with any remaining qty
            if qty_base > 0:
                if pos.qty > 0:
                    new_qty = pos.qty + qty_base
                    pos.avg_price = (pos.avg_price * pos.qty + price * qty_base) / new_qty
                    pos.qty = new_qty
                else:  # was flat
                    pos.qty = qty_base
                    pos.avg_price = price
                    pos.ts = time.time()
        else:  # sell
            # Cash inflow for sells
            self.cash_usd += qty_base * price
            if pos.qty > 0:
                close_qty = min(qty_base, pos.qty)
                realized_delta += close_qty * (price - pos.avg_price)
                pos.qty -= close_qty
                qty_base -= close_qty
                if pos.qty == 0:
                    pos.avg_price = 0.0
            if qty_base > 0:  # open/increase short with remaining
                if pos.qty < 0:
                    new_abs = (-pos.qty) + qty_base
                    pos.avg_price = ((-pos.qty) * pos.avg_price + price * qty_base) / new_abs
                    pos.qty = -new_abs
                else:  # was flat
                    pos.qty = -qty_base
                    pos.avg_price = price
        # Deduct fee from cash
        self.cash_usd -= fee
        self.realized_pnl_usd += realized_delta
        pos.ts = time.time()  # update timestamp whenever fill occurs
        self.positions[symbol] = pos
        return {
            "realized_delta": realized_delta,
            "pos_qty": pos.qty,
            "pos_avg": pos.avg_price,
        }

    def equity(self, prices: Dict[str, float]) -> float:
        eq = self.cash_usd
        for sym, pos in self.positions.items():
            eq += pos.qty * prices.get(sym, pos.avg_price)
        return eq

    def unrealized_total(self, prices: Dict[str, float]) -> float:
        u = 0.0
        for sym, pos in self.positions.items():
            mark = prices.get(sym, pos.avg_price)
            u += pos.qty * (mark - pos.avg_price)
        return u

    def open_notional(self, prices: Dict[str, float]) -> float:
        """Absolute USD exposure of all open positions (long + short)."""
        notional = 0.0
        for sym, pos in self.positions.items():
            mark = prices.get(sym, pos.avg_price)
            notional += abs(pos.qty) * mark
        return notional

    # ---- helpers for risk manager ----
    def update_mark(self, symbol: str, price: float):
        self._latest_prices[symbol] = price

    def latest_prices(self) -> Dict[str, float]:
        return self._latest_prices

    def position_snapshot(self):
        for sym, pos in self.positions.items():
            if pos.qty != 0:
                return {
                    "symbol": sym,
                    "qty": pos.qty,
                    "avg": pos.avg_price,
                    "ts": pos.ts,
                }
        return None
