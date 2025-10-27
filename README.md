# WOOFi Perp Bot Framework

A modular, config-driven starter kit for building trading bots on WOOFi Perps (and beyond). Includes:

- Core exchange wrappers (paper trading now, WOOFi stub for extension)
- Pluggable strategies (liquidity gap, mean reversion, trend follower)
- Risk manager (SL/TP, max exposure, daily loss limit)
- Backtesting engine (candles CSV) and paper-trading mode
- Config-first design via YAML and .env

## Quickstart

1) Create and activate a virtual environment (recommended).

2) Install dependencies:

```bash
pip install -r requirements.txt
```

3) Copy example config and edit:

```bash
copy examples\config.example.yaml config.yaml
```

4) Run in paper mode:

```bash
python run.py --config config.yaml
```

## Repo Structure

```
woofi-perp-bot/
  run.py
  config.yaml                # your runtime config (example in examples/)
  requirements.txt
  README.md
  LICENSE
  .gitignore
  .env.example
  data/
    sample_candles/
      ETH-USDT_1m.csv        # tiny sample for backtesting
  examples/
    config.example.yaml
  woofibot/
    __init__.py
    utils/
      config.py
      logger.py
    core/
      order.py
      portfolio.py
      exchange_base.py
      paper_exchange.py
      woofi_exchange.py      # stub
    risk/
      risk_manager.py
    strategies/
      __init__.py
      base.py
      liquidity_gap.py
      mean_reversion.py
      trend_follower.py
    backtest/
      engine.py
```

## Config

See `examples/config.example.yaml` for all options. Key fields:
- `mode`: paper | backtest
- `strategy`: liquidity_gap | mean_reversion | trend_follower
- `markets`: ["BTC-USDT", "ETH-USDT"]
- `order_size`: 50.0
- `min_spread`: 0.15  # percent
- `loop_interval_ms`: 1000
- `risk`: { max_exposure, stop_loss_pct, take_profit_pct, daily_loss_limit_pct }
- `exchange`: paper | woofi-paper (paper execution driven by live WOOFi market data; coming soon)

## Backtesting

Point to a CSV in `data/sample_candles/` or your own. Minimal schema:
`timestamp,open,high,low,close,volume`

Run with mode `backtest`.

## Dashboard

A Streamlit dashboard visualizes live equity and trades from CSV logs.

- Start the bot (paper or backtest) to generate `logs/equity.csv` and `logs/trades.csv`.
- In a new terminal, run:

```bash
streamlit run dashboard/app.py
```

Panels:
- Equity curve (auto-refreshes)
- Recent trades table with price/size/fee and equity snapshot
- Key analytics: Win rate, Avg Win/Loss, Max Drawdown, Estimated Exposure

CSV columns written by the bot:
- `logs/equity.csv`: ts, equity, cash, realized_total, unrealized
- `logs/trades.csv`: ts, symbol, side, price, qty_quote, fee, realized_delta, realized_total, unrealized, equity_after, cash_after, pos_qty, pos_avg

## Extend

- Add strategies in `woofibot/strategies/` by subclassing `StrategyBase`.
- Implement real WOOFi integration in `woofibot/core/woofi_exchange.py`.
- Add dashboards (Streamlit) and log sinks as needed.

## License

MIT
