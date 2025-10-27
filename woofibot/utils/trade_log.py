from pathlib import Path
import csv
import time
from typing import Dict, Optional


class TradeLogger:
    def __init__(self, trades_path: str = "logs/trades.csv", equity_path: str = "logs/equity.csv"):
        self.trades_path = Path(trades_path)
        self.equity_path = Path(equity_path)
        self.trades_path.parent.mkdir(parents=True, exist_ok=True)
        self.equity_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_trades_header()
        self._ensure_equity_header()

    def _ensure_trades_header(self):
        if not self.trades_path.exists() or self.trades_path.stat().st_size == 0:
            with self.trades_path.open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow([
                    "ts","symbol","side","price","qty_quote","fee",
                    "realized_delta","realized_total","unrealized",
                    "equity_after","cash_after","pos_qty","pos_avg"
                ])

    def _ensure_equity_header(self):
        if not self.equity_path.exists() or self.equity_path.stat().st_size == 0:
            with self.equity_path.open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["ts","equity","cash","realized_total","unrealized"]) 

    def log_trade(self, trade: Dict, equity: Optional[float] = None, cash: Optional[float] = None):
        ts = trade.get("ts") or time.time()
        with self.trades_path.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([
                ts,
                trade.get("symbol"),
                trade.get("side"),
                trade.get("price"),
                trade.get("qty_quote"),
                trade.get("fee", 0.0),
                trade.get("realized_delta", ""),
                trade.get("realized_total", ""),
                trade.get("unrealized", ""),
                trade.get("equity_after", equity if equity is not None else ""),
                trade.get("cash_after", cash if cash is not None else ""),
                trade.get("pos_qty", ""),
                trade.get("pos_avg", ""),
            ])

    def log_equity(self, equity: float, cash: float, realized_total: Optional[float] = None, unrealized: Optional[float] = None):
        ts = time.time()
        with self.equity_path.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([ts, equity, cash, realized_total if realized_total is not None else "", unrealized if unrealized is not None else ""]) 
