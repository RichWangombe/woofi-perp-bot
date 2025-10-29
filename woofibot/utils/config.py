from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import yaml
from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv
import os


class RiskConfig(BaseModel):
    max_exposure_usd: float = 0.0
    max_notional_per_trade: float = 0.0
    stop_loss_pct: float = 0.0
    take_profit_pct: float = 0.0
    daily_loss_limit_pct: float = 0.0
    max_position_age_sec: int | None = None


class BacktestConfig(BaseModel):
    data_dir: str = "data/sample_candles"
    timeframe: str = "1m"
    fee_bps: float = 0.0


class WOOFiConfig(BaseModel):
    rest_url: str = os.getenv("WOOFI_API_BASE", "")
    ws_url: Optional[str] = None
    poll_interval_ms: int = 1000
    rest_orderbook: Optional[str] = None
    rest_ticker: Optional[str] = None
    rest_bookticker: Optional[str] = None
    rest_pricechanges: Optional[str] = None
    simulate_latency_ms: int = 0


class LoggingConfig(BaseModel):
    backend: str = "csv"  # csv | sqlite
    trades_csv_path: str = "logs/trades.csv"
    equity_csv_path: str = "logs/equity.csv"
    sqlite_path: str = "logs/trading.db"


class Config(BaseModel):
    mode: str
    strategy: str
    markets: List[str]
    order_size: float
    loop_interval_ms: int = 1000
    exchange: str = "paper"  # paper | woofi-paper | woofi-live (future)
    risk: RiskConfig = RiskConfig()
    strategy_params: Dict[str, Any] = {}
    backtest: BacktestConfig = BacktestConfig()
    woofi: WOOFiConfig = WOOFiConfig()
    logging: LoggingConfig = LoggingConfig()


def load_config(path: str) -> Config:
    load_dotenv()
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Config(**data)
