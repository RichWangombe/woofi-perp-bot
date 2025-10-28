import time
from typing import Dict, List, Tuple, Optional, Any

import requests


def _to_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


class WOOFiPollAdapter:
    """
    Config-driven polling adapter for REST orderbook/ticker.
    Tries depth first (bids/asks), then bookTicker (bid/ask), then simple ticker (last/price).
    """

    def __init__(
        self,
        rest_orderbook: Optional[str],
        rest_ticker: Optional[str],
        symbols: List[str],
        poll_interval_ms: int = 1000,
        rest_bookticker: Optional[str] = None,
        simulate_latency_ms: int = 0,
    ):
        self.rest_orderbook = rest_orderbook or ""
        self.rest_ticker = rest_ticker or ""
        self.rest_bookticker = rest_bookticker or ""
        self.symbols = symbols
        self.poll_interval_ms = poll_interval_ms
        self.simulate_latency_ms = simulate_latency_ms
        self.last_fetch_ts = 0.0
        self.best_quotes: Dict[str, Tuple[Optional[float], Optional[float]]] = {s: (None, None) for s in symbols}
        self.marks: Dict[str, Optional[float]] = {s: None for s in symbols}
        self._backoff = 1.0

    def step(self):
        now = time.time()
        if (now - self.last_fetch_ts) * 1000.0 < self.poll_interval_ms:
            return
        for sym in self.symbols:
            try:
                self._fetch_symbol(sym)
                self._backoff = 1.0
            except Exception:
                time.sleep(self._backoff)
                self._backoff = min(self._backoff * 2.0, 10.0)
        self.last_fetch_ts = now

    def _fetch_symbol(self, symbol: str):
        # optional artificial latency to smooth UI
        if self.simulate_latency_ms > 0:
            time.sleep(self.simulate_latency_ms / 1000.0)

        bb: Optional[float] = None
        ba: Optional[float] = None

        # Attempt 1: orderbook depth with bids/asks
        if self.rest_orderbook:
            try:
                url = self.rest_orderbook.format(symbol=symbol)
                r = requests.get(url, timeout=6)
                r.raise_for_status()
                data = r.json()
                bids = data.get("bids") or []
                asks = data.get("asks") or []
                # bids/asks can be list of [price, qty] (possibly strings)
                if isinstance(bids, list) and bids:
                    p = _to_float(bids[0][0] if isinstance(bids[0], (list, tuple)) else None)
                    if p is not None:
                        bb = p
                if isinstance(asks, list) and asks:
                    p = _to_float(asks[0][0] if isinstance(asks[0], (list, tuple)) else None)
                    if p is not None:
                        ba = p
            except Exception:
                pass

        # Attempt 2: bookTicker-style endpoint (bidPrice/askPrice)
        if (bb is None or ba is None) and self.rest_bookticker:
            try:
                turl = self.rest_bookticker.format(symbol=symbol)
                r2 = requests.get(turl, timeout=5)
                r2.raise_for_status()
                td = r2.json()
                bid = _to_float(td.get("bidPrice") or td.get("bid") or td.get("bestBid"))
                ask = _to_float(td.get("askPrice") or td.get("ask") or td.get("bestAsk"))
                if bid is not None:
                    bb = bid if bb is None else bb
                if ask is not None:
                    ba = ask if ba is None else ba
            except Exception:
                pass

        # Attempt 3: simple ticker (last/price)
        if (bb is None or ba is None) and self.rest_ticker:
            try:
                turl = self.rest_ticker.format(symbol=symbol)
                r3 = requests.get(turl, timeout=5)
                r3.raise_for_status()
                td2 = r3.json()
                last = _to_float(td2.get("last") or td2.get("price") or td2.get("p"))
                if last is not None:
                    if bb is None:
                        bb = last
                    if ba is None:
                        ba = last
            except Exception:
                pass

        # Debug print to verify adapter sees prices
        print(f"[DBG] {symbol} bid={bb} ask={ba} mark={self.marks.get(symbol)}")
        self.best_quotes[symbol] = (bb, ba)
        if bb is not None and ba is not None:
            self.marks[symbol] = (bb + ba) / 2.0
        elif bb is not None:
            self.marks[symbol] = bb
        elif ba is not None:
            self.marks[symbol] = ba

    def get_orderbook(self, symbol: str) -> Tuple[Optional[float], Optional[float]]:
        return self.best_quotes.get(symbol, (None, None))

    def get_mark(self, symbol: str) -> Optional[float]:
        return self.marks.get(symbol)
