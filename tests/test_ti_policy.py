import time
from woofibot.risk.ti_policy import TIPolicy
from woofibot.utils.config import TIConfig
from woofibot.core.portfolio import Portfolio, Position


def test_ti_policy_blocks_micro_and_pingpong_then_allows_after_intervals():
    cfg = TIConfig(min_order_notional=100, min_hold_time_sec=2, min_trade_interval_sec=1)
    tip = TIPolicy(cfg)

    pf = Portfolio()
    prices = {"X": 2000.0}

    # 1) Micro order should be blocked
    od_small = {"symbol": "X", "side": "buy", "qty_quote": 50}
    assert tip.allow_signal(od_small, pf, prices) is False

    # 2) Valid open allowed
    od = {"symbol": "X", "side": "buy", "qty_quote": 200}
    assert tip.allow_signal(od, pf, prices) is True
    tip.record_fill("X")

    # Simulate open position
    pf.positions["X"] = Position(qty=0.1, avg_price=2000.0, ts=time.time())

    # 3) Immediate close within hold time should be blocked
    od_close = {"symbol": "X", "side": "sell", "qty_quote": 200}
    assert tip.allow_signal(od_close, pf, prices) is False

    # 4) Another open too soon (trade interval) blocked
    assert tip.allow_signal(od, pf, prices) is False

    # 5) After interval and hold time, closing allowed
    time.sleep(2.1)
    assert tip.allow_signal(od_close, pf, prices) is True
