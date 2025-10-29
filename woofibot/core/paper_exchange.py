from typing import Dict, Tuple, Optional, List
import time
import pandas as pd
from pathlib import Path
from .exchange_base import ExchangeBase
from .order import Order, Fill
from .portfolio import Portfolio


class PaperExchange(ExchangeBase):
    def __init__(self, symbols: List[str], data_dir: str, fee_bps: float = 2.0, market_data_source: Optional[object] = None):
        self.symbols = symbols
        self.fee_bps = fee_bps
        self.ptr = 0
        self.books: Dict[str, pd.DataFrame] = {}
        self.prices: Dict[str, float] = {}
        self.portfolio = Portfolio()
        self.market_data = market_data_source
        for sym in symbols:
            path = Path(data_dir) / f"{sym}_1m.csv"
            if not path.exists():
                # create a trivial single-line dataframe if missing
                df = pd.DataFrame([[0, 2000, 2005, 1995, 2002, 0]], columns=["timestamp","open","high","low","close","volume"])
            else:
                df = pd.read_csv(path)
            self.books[sym] = df.reset_index(drop=True)
            self.prices[sym] = float(df.iloc[0]["close"]) if len(df) else 2000.0

    def get_orderbook(self, symbol: str) -> Tuple[float, float]:
        # Prefer external market data if provided
        if self.market_data is not None:
            bb, ba = self.market_data.get_orderbook(symbol)
            if bb is not None and ba is not None:
                return bb, ba
        p = self.prices[symbol]
        spread = max(0.5, p * 0.0008)  # 8 bps min spread
        return p - spread/2, p + spread/2

    def place_order(self, symbol: str, side: str, qty_quote: float, price: Optional[float] = None) -> Dict:
        best_bid, best_ask = self.get_orderbook(symbol)
        trade_price = best_ask if side == "buy" else best_bid
        mid = (best_bid + best_ask) / 2.0 if best_bid is not None and best_ask is not None else trade_price
        # positive bps means worse than mid for both sides
        if mid and mid > 0:
            if side == "buy":
                slippage_bps = ((trade_price - mid) / mid) * 10000.0
            else:
                slippage_bps = ((mid - trade_price) / mid) * 10000.0
        else:
            slippage_bps = 0.0
        qty_base = qty_quote / trade_price if trade_price > 0 else 0
        fee = abs(qty_quote) * (self.fee_bps / 10000.0)
        info = self.portfolio.update_fill(symbol, side, qty_base, trade_price, fee)
        prices = self.get_prices()
        return {
            "ts": time.time(),
            "symbol": symbol,
            "side": side,
            "price": trade_price,
            "mid": mid,
            "slippage_bps": slippage_bps,
            "qty_quote": qty_quote,
            "fee": fee,
            "realized_delta": info.get("realized_delta", 0.0),
            "realized_total": self.portfolio.realized_pnl_usd,
            "unrealized": self.portfolio.unrealized_total(prices),
            "equity_after": self.portfolio.equity(prices),
            "cash_after": self.portfolio.cash_usd,
            "pos_qty": info.get("pos_qty"),
            "pos_avg": info.get("pos_avg"),
        }

    def get_prices(self) -> Dict[str, float]:
        return dict(self.prices)

    def step(self):
        # If external market data is present, poll it and update marks; otherwise advance candles
        if self.market_data is not None:
            # adapter implements synchronous step()
            try:
                self.market_data.step()
            except Exception:
                pass
            for sym in self.symbols:
                mark = self.market_data.get_mark(sym)
                if mark is not None:
                    self.prices[sym] = float(mark)
        else:
            # advance one candle
            for sym, df in self.books.items():
                if self.ptr < len(df):
                    self.prices[sym] = float(df.iloc[self.ptr]["close"])
            self.ptr += 1
