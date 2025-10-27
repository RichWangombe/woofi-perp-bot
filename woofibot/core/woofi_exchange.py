# Stub for real WOOFi integration.
# Implement REST/WebSocket auth, order placement, balances, orderbook, etc.
from .exchange_base import ExchangeBase
from typing import Dict, Tuple, Optional


class WOOFiExchange(ExchangeBase):
    def __init__(self, api_key: str, api_secret: str, base_url: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url

    def get_orderbook(self, symbol: str):
        raise NotImplementedError("Implement WOOFi orderbook fetch")

    def place_order(self, symbol: str, side: str, qty_quote: float, price: Optional[float] = None):
        raise NotImplementedError("Implement WOOFi place_order")

    def get_prices(self) -> Dict[str, float]:
        raise NotImplementedError("Implement WOOFi tickers")

    def step(self):
        # no-op for live exchange
        pass
