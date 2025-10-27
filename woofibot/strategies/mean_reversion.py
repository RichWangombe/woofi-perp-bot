from typing import List, Dict
from .base import StrategyBase


class MeanReversionStrategy(StrategyBase):
    def on_tick(self, symbol_prices: Dict[str, float], exchange, risk_mgr) -> List[Dict]:
        # Placeholder: no-op
        return []
