from abc import ABC, abstractmethod
from typing import List, Dict


class StrategyBase(ABC):
    def __init__(self, params: Dict):
        self.params = params or {}

    @abstractmethod
    def on_tick(self, symbol_prices: Dict[str, float], exchange, risk_mgr) -> List[Dict]:
        """Return list of order dicts: {symbol, side, qty_quote}"""
        raise NotImplementedError
