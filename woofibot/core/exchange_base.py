from abc import ABC, abstractmethod
from typing import Dict, Tuple, Optional


class ExchangeBase(ABC):
    @abstractmethod
    def get_orderbook(self, symbol: str) -> Tuple[float, float]:
        """Return (best_bid, best_ask)"""
        raise NotImplementedError

    @abstractmethod
    def place_order(self, symbol: str, side: str, qty_quote: float, price: Optional[float] = None) -> Dict:
        raise NotImplementedError

    @abstractmethod
    def get_prices(self) -> Dict[str, float]:
        raise NotImplementedError

    @abstractmethod
    def step(self):
        """Advance simulation (paper/backtest). Real exchange can be no-op."""
        raise NotImplementedError
