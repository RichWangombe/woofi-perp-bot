import time
from typing import Dict, List, Tuple, Optional

import requests


class WOOFiPollAdapter:
    """
    Config-driven polling adapter for WOOFi (or any REST orderbook/ticker).
    Requires woofi.rest_orderbook and/or woofi.rest_ticker with {symbol} placeholder.
    """

    def __init__(self, rest_orderbook: str, rest_ticker: Optional[str], symbols: List[str], poll_interval_ms: int = 1000):
        self.rest_orderbook = rest_orderbook
        self.rest_ticker = rest_ticker
        self.symbols = symbols
        self.poll_interval_ms = poll_interval_ms
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
        bb = None
        ba = None
        if self.rest_orderbook:
            url = self.rest_orderbook.format(symbol=symbol)
            r = requests.get(url, timeout=5)
            r.raise_for_status()
            data = r.json()
            # Expecting {'bids': [[price, qty],...], 'asks': [[price, qty],...]}
            bids = data.get("bids") or []
            asks = data.get("asks") or []
            if bids:
                bb = float(bids[0][0])
            if asks:
                ba = float(asks[0][0])
        if bb is None or ba is None:
            # Fallback to ticker
            if self.rest_ticker:
                turl = self.rest_ticker.format(symbol=symbol)
                r2 = requests.get(turl, timeout=5)
                r2.raise_for_status()
                td = r2.json()
                # Expecting {'last': price} or similar
                last = td.get("last") or td.get("price")
                if last is not None:
                    last = float(last)
                    bb = last if bb is None else bb
                    ba = last if ba is None else ba
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
