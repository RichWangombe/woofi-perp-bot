from typing import Dict
from ..core.portfolio import Portfolio


class RiskManager:
    def __init__(self, portfolio: Portfolio, config):
        self.pf = portfolio
        self.cfg = config
        self.start_equity = portfolio.cash_usd

    def can_trade(self, prices: Dict[str, float]) -> bool:
        # daily loss limit check
        eq = self.pf.equity(prices)
        dd_pct = (self.start_equity - eq) / max(1e-9, self.start_equity) * 100
        if dd_pct >= self.cfg.daily_loss_limit_pct:
            return False
        return True
