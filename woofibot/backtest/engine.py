from typing import Optional


def run_backtest(exchange, strategy, risk_mgr, max_steps: int = 500, trade_logger: Optional[object] = None):
    results = []
    for _ in range(max_steps):
        exchange.step()
        prices = exchange.get_prices()
        equity = exchange.portfolio.equity(prices)
        cash = exchange.portfolio.cash_usd
        realized_total = exchange.portfolio.realized_pnl_usd
        unrealized = exchange.portfolio.unrealized_total(prices)
        if trade_logger is not None:
            trade_logger.log_equity(equity, cash, realized_total=realized_total, unrealized=unrealized)
        if not risk_mgr.can_trade(prices):
            continue
        orders = strategy.on_tick(prices, exchange, risk_mgr)
        for od in orders:
            res = exchange.place_order(od["symbol"], od["side"], od["qty_quote"])
            results.append(res)
            if trade_logger is not None:
                trade_logger.log_trade(res, equity=exchange.portfolio.equity(exchange.get_prices()), cash=exchange.portfolio.cash_usd)
    return results
