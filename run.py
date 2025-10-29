import argparse
import time
from woofibot.utils.config import load_config
from woofibot.utils.logger import setup_logger
from woofibot.utils.trade_log import TradeLogger
from woofibot.utils.trade_log_sqlite import SQLiteTradeLogger
from woofibot.core.paper_exchange import PaperExchange
from woofibot.core.woofi_exchange import WOOFiExchange
from woofibot.exchange.woofi_poll_adapter import WOOFiPollAdapter
from woofibot.strategies import LiquidityGapStrategy, MeanReversionStrategy, TrendFollowerStrategy
from woofibot.risk.risk_manager import RiskManager
from woofibot.risk.ti_policy import TIPolicy
from woofibot.backtest.engine import run_backtest


def build_strategy(name: str, params):
    if name == "liquidity_gap":
        return LiquidityGapStrategy(params.get("liquidity_gap", {}))
    if name == "mean_reversion":
        return MeanReversionStrategy(params.get("mean_reversion", {}))
    if name == "trend_follower":
        return TrendFollowerStrategy(params.get("trend_follower", {}))
    raise ValueError(f"Unknown strategy {name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    cfg = load_config(args.config)
    logger = setup_logger()
    logger.info(f"Loaded config: {cfg}")
    # Select logging backend
    if getattr(cfg, "logging", None) and cfg.logging.backend == "sqlite":
        trade_logger = SQLiteTradeLogger(cfg.logging.sqlite_path)
    else:
        trade_logger = TradeLogger(
            trades_path=getattr(cfg.logging, "trades_csv_path", "logs/trades.csv"),
            equity_path=getattr(cfg.logging, "equity_csv_path", "logs/equity.csv"),
        )

    live_client = None
    ti_policy = TIPolicy(cfg.ti)
    if cfg.mode == "backtest":
        exch = PaperExchange(cfg.markets, cfg.backtest.data_dir, cfg.backtest.fee_bps)
    else:
        ex_kind = getattr(cfg, "exchange", "paper")
        if ex_kind == "woofi-live":
            # Use WOOFi poller for live prices, keep PaperExchange as a shadow portfolio/logging engine
            md = WOOFiPollAdapter(
                rest_orderbook=cfg.woofi.rest_orderbook or "",
                rest_ticker=cfg.woofi.rest_ticker or None,
                symbols=cfg.markets,
                poll_interval_ms=cfg.woofi.poll_interval_ms,
                rest_bookticker=getattr(cfg.woofi, "rest_bookticker", None) or None,
                rest_pricechanges=getattr(cfg.woofi, "rest_pricechanges", None) or None,
                simulate_latency_ms=getattr(cfg.woofi, "simulate_latency_ms", 0),
            )
            exch = PaperExchange(cfg.markets, cfg.backtest.data_dir, cfg.backtest.fee_bps, market_data_source=md)
            # instantiate live REST client (testnet defaults; requires env keys)
            live_client = WOOFiExchange(base_url=(cfg.woofi.order_base_url or None), testnet=getattr(cfg.woofi, "testnet", True))
        elif ex_kind == "woofi-paper":
            md = WOOFiPollAdapter(
                rest_orderbook=cfg.woofi.rest_orderbook or "",
                rest_ticker=cfg.woofi.rest_ticker or None,
                symbols=cfg.markets,
                poll_interval_ms=cfg.woofi.poll_interval_ms,
                rest_bookticker=getattr(cfg.woofi, "rest_bookticker", None) or None,
                rest_pricechanges=getattr(cfg.woofi, "rest_pricechanges", None) or None,
                simulate_latency_ms=getattr(cfg.woofi, "simulate_latency_ms", 0),
            )
            exch = PaperExchange(cfg.markets, cfg.backtest.data_dir, cfg.backtest.fee_bps, market_data_source=md)
        else:
            exch = PaperExchange(cfg.markets, cfg.backtest.data_dir, cfg.backtest.fee_bps)

    strat = build_strategy(cfg.strategy, cfg.strategy_params)
    # let strategy know about order_size from top-level config as optional override
    if hasattr(strat, "params") and "order_size_override" not in strat.params:
        strat.params["order_size_override"] = cfg.order_size

    risk_mgr = RiskManager(exch.portfolio, cfg.risk)

    if cfg.mode == "backtest":
        logger.info("Starting backtest...")
        results = run_backtest(exch, strat, risk_mgr, max_steps=1000, trade_logger=trade_logger)
        logger.info(f"Backtest finished: {len(results)} orders executed")
        return

    logger.info("Starting paper loop... (Ctrl+C to stop)")
    try:
        while True:
            exch.step()
            prices = exch.get_prices()
            # update marks in portfolio for risk calculations
            for sym, mk in prices.items():
                exch.portfolio.update_mark(sym, mk)

            # ---- auto-close check ----
            close_od = risk_mgr.check_auto_close(prices)
            if close_od:
                # send live close first (if enabled), then shadow it locally
                if live_client:
                    try:
                        live_client.place_order(close_od["symbol"], close_od["side"], close_od["qty_quote"])
                        logger.info(f"LIVE_SENT close: {close_od}")
                    except Exception as e:
                        logger.warning(f"LIVE_CLOSE_FAILED: {e}")
                res = exch.place_order(close_od["symbol"], close_od["side"], close_od["qty_quote"])
                ti_policy.record_fill(close_od["symbol"])
                trade_logger.log_trade(res, equity=res.get("equity_after"), cash=res.get("cash_after"))
                logger.info(f"Auto-closed: {res} reason={close_od['reason']}\n")
            else:
                # ---- trading block ----
                order_notional = cfg.order_size
                if risk_mgr.can_trade(prices, order_notional):
                    orders = strat.on_tick(prices, exch, risk_mgr)
                    for od in orders:
                        # TI policy filters to avoid spam / ping-pong / micro trades
                        if not ti_policy.allow_signal(od, exch.portfolio, prices):
                            continue
                        if live_client:
                            try:
                                live_client.place_order(od["symbol"], od["side"], od["qty_quote"])
                                logger.info(f"LIVE_SENT: {od}")
                            except Exception as e:
                                logger.warning(f"LIVE_SEND_FAILED: {e}")
                        res = exch.place_order(od["symbol"], od["side"], od["qty_quote"])
                        ti_policy.record_fill(od["symbol"]) 
                        trade_logger.log_trade(res, equity=res.get("equity_after"), cash=res.get("cash_after"))
                        logger.info(f"Filled: {res}\n")

            # ---- equity snapshot AFTER potential fills ----
            prices = exch.get_prices()  # refresh marks in case fills affected state
            equity = exch.portfolio.equity(prices)
            cash = exch.portfolio.cash_usd
            realized_total = exch.portfolio.realized_pnl_usd
            unrealized = exch.portfolio.unrealized_total(prices)
            trade_logger.log_equity(equity, cash, realized_total=realized_total, unrealized=unrealized)
            time.sleep(cfg.loop_interval_ms / 1000.0)
    except KeyboardInterrupt:
        logger.info("Stopped.")


if __name__ == "__main__":
    main()
