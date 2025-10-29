import time
from woofibot.risk.risk_manager import RiskManager
from woofibot.utils.config import RiskConfig

class DummyPF:
    def __init__(self):
        # one open position sized to ~1000 USD notional
        self.positions = {"PERP_ETH_USDC": type("P", (), {"qty": 0.5, "avg_price": 2000.0, "ts": time.time()-120})()}
    def open_notional(self, _):
        return 0.5 * 2000
    def equity(self, _):
        return 1000.0

def test_block_new_exposure():
    cfg = RiskConfig(max_exposure_usd=300, daily_loss_limit_pct=1000)
    rm = RiskManager(DummyPF(), cfg)
    assert rm.can_trade({}, 50) is False
