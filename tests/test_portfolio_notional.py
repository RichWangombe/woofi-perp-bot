import pytest
from woofibot.core.portfolio import Portfolio, Position


def test_open_notional_long_short_and_fallback():
    pf = Portfolio()
    # Long 0.1 @ 2000, mark 2100 -> 210
    pf.positions["A"] = Position(qty=0.1, avg_price=2000.0)
    # Short 0.2 @ 3000, mark 2900 -> abs(-0.2)*2900 = 580
    pf.positions["B"] = Position(qty=-0.2, avg_price=3000.0)
    # Missing price -> fallback to avg_price 100 -> 0.5*100 = 50
    pf.positions["C"] = Position(qty=0.5, avg_price=100.0)

    prices = {"A": 2100.0, "B": 2900.0}
    notional = pf.open_notional(prices)
    assert notional == pytest.approx(210.0 + 580.0 + 50.0, rel=1e-9)
