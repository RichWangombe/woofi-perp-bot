import math
from pathlib import Path

from woofibot.core.paper_exchange import PaperExchange


class MarketStub:
    def __init__(self, symbols):
        self.bb = {s: None for s in symbols}
        self.ba = {s: None for s in symbols}
        self.mk = {s: None for s in symbols}

    def set_quote(self, symbol, bid, ask, mark=None):
        self.bb[symbol] = bid
        self.ba[symbol] = ask
        self.mk[symbol] = mark if mark is not None else (bid + ask) / 2 if (bid and ask) else None

    def get_orderbook(self, symbol):
        return self.bb.get(symbol), self.ba.get(symbol)

    def get_mark(self, symbol):
        return self.mk.get(symbol)

    def step(self):
        pass


def test_long_open_close_realized_unrealized():
    sym = "ETH-USDT"
    md = MarketStub([sym])
    # initial quotes 100/100 -> mark 100
    md.set_quote(sym, 100.0, 100.0, 100.0)
    ex = PaperExchange([sym], data_dir=str(Path.cwd() / "__not_used__"), fee_bps=0.0, market_data_source=md)

    # advance to set mark price
    ex.step()
    assert ex.get_prices()[sym] == 100.0

    # buy 100 USDT -> 1 base at 100
    res_buy = ex.place_order(sym, "buy", qty_quote=100.0)
    assert math.isclose(res_buy["price"], 100.0, rel_tol=1e-9)
    assert math.isclose(ex.portfolio.positions[sym].qty, 1.0, rel_tol=1e-9)
    assert math.isclose(ex.portfolio.positions[sym].avg_price, 100.0, rel_tol=1e-9)

    # mark up to 110
    md.set_quote(sym, 110.0, 110.0, 110.0)
    ex.step()
    unreal = ex.portfolio.unrealized_total(ex.get_prices())
    assert math.isclose(unreal, 10.0, rel_tol=1e-9)

    # sell 50 USDT -> 0.4545 base? No, trade price 110 => 50/110 = 0.45454 base closed
    res_sell_half = ex.place_order(sym, "sell", qty_quote=50.0)
    # realized delta for closed qty: (110-100)*0.45454...
    closed_qty = 50.0 / 110.0
    expected_realized = (110.0 - 100.0) * closed_qty
    assert math.isclose(res_sell_half["realized_delta"], expected_realized, rel_tol=1e-6)
    # remaining position qty
    remaining_qty = 1.0 - closed_qty
    assert math.isclose(ex.portfolio.positions[sym].qty, remaining_qty, rel_tol=1e-6)
    assert math.isclose(ex.portfolio.positions[sym].avg_price, 100.0, rel_tol=1e-9)

    # move mark to 90 and close the rest
    md.set_quote(sym, 90.0, 90.0, 90.0)
    ex.step()
    res_sell_rest = ex.place_order(sym, "sell", qty_quote=remaining_qty * 90.0)
    expected_realized2 = (90.0 - 100.0) * remaining_qty
    assert math.isclose(res_sell_rest["realized_delta"], expected_realized2, rel_tol=1e-6)
    # total realized should net to ~0 given + and - legs
    assert math.isclose(ex.portfolio.realized_pnl_usd, expected_realized + expected_realized2, rel_tol=1e-6)
    # flat position
    assert math.isclose(ex.portfolio.positions[sym].qty, 0.0, abs_tol=1e-12)


def test_short_open_close():
    sym = "ETH-USDT"
    md = MarketStub([sym])
    md.set_quote(sym, 200.0, 200.0, 200.0)
    ex = PaperExchange([sym], data_dir=str(Path.cwd() / "__not_used__"), fee_bps=0.0, market_data_source=md)
    ex.step()

    # open short: sell 100 USDT at 200 => qty_base = 0.5 short
    res_open_short = ex.place_order(sym, "sell", qty_quote=100.0)
    assert math.isclose(ex.portfolio.positions[sym].qty, -0.5, rel_tol=1e-9)
    assert math.isclose(ex.portfolio.positions[sym].avg_price, 200.0, rel_tol=1e-9)

    # mark down to 180
    md.set_quote(sym, 180.0, 180.0, 180.0)
    ex.step()
    # buy to close all: need 0.5 * 180 = 90 USDT
    res_close = ex.place_order(sym, "buy", qty_quote=90.0)
    # realized: (avg - buy_price) * qty_closed
    qty_closed = 90.0 / 180.0
    expected_realized = (200.0 - 180.0) * qty_closed
    assert math.isclose(res_close["realized_delta"], expected_realized, rel_tol=1e-9)
    assert math.isclose(ex.portfolio.positions[sym].qty, 0.0, abs_tol=1e-12)


def test_get_orderbook_uses_external_quotes():
    sym = "ETH-USDT"
    md = MarketStub([sym])
    md.set_quote(sym, 100.0, 101.0)
    ex = PaperExchange([sym], data_dir=str(Path.cwd() / "__not_used__"), fee_bps=0.0, market_data_source=md)
    bb, ba = ex.get_orderbook(sym)
    assert math.isclose(bb, 100.0, rel_tol=1e-9)
    assert math.isclose(ba, 101.0, rel_tol=1e-9)
