import sqlite3
from pathlib import Path
import time
from typing import Dict, Optional


class SQLiteTradeLogger:
    def __init__(self, db_path: str = "logs/trading.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        # isolation_level=None enables autocommit
        return sqlite3.connect(self.db_path.as_posix(), timeout=5)

    def _init_db(self):
        with self._connect() as conn:
            c = conn.cursor()
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS trades (
                  ts REAL,
                  symbol TEXT,
                  side TEXT,
                  price REAL,
                  qty_quote REAL,
                  fee REAL,
                  realized_delta REAL,
                  realized_total REAL,
                  unrealized REAL,
                  equity_after REAL,
                  cash_after REAL,
                  pos_qty REAL,
                  pos_avg REAL
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS equity (
                  ts REAL,
                  equity REAL,
                  cash REAL,
                  realized_total REAL,
                  unrealized REAL
                )
                """
            )
            c.execute("CREATE INDEX IF NOT EXISTS ix_trades_ts ON trades(ts)")
            c.execute("CREATE INDEX IF NOT EXISTS ix_equity_ts ON equity(ts)")
            conn.commit()

    def log_trade(self, trade: Dict, equity: Optional[float] = None, cash: Optional[float] = None):
        ts = float(trade.get("ts") or time.time())
        row = (
            ts,
            trade.get("symbol"),
            trade.get("side"),
            float(trade.get("price")) if trade.get("price") is not None else None,
            float(trade.get("qty_quote")) if trade.get("qty_quote") is not None else None,
            float(trade.get("fee", 0.0)),
            float(trade.get("realized_delta", 0.0)) if trade.get("realized_delta") is not None else None,
            float(trade.get("realized_total", 0.0)) if trade.get("realized_total") is not None else None,
            float(trade.get("unrealized", 0.0)) if trade.get("unrealized") is not None else None,
            float(trade.get("equity_after", equity if equity is not None else 0.0)),
            float(trade.get("cash_after", cash if cash is not None else 0.0)),
            float(trade.get("pos_qty", 0.0)) if trade.get("pos_qty") is not None else None,
            float(trade.get("pos_avg", 0.0)) if trade.get("pos_avg") is not None else None,
        )
        with self._connect() as conn:
            c = conn.cursor()
            c.execute(
                """
                INSERT INTO trades (
                    ts, symbol, side, price, qty_quote, fee,
                    realized_delta, realized_total, unrealized,
                    equity_after, cash_after, pos_qty, pos_avg
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                row,
            )
            conn.commit()

    def log_equity(self, equity: float, cash: float, realized_total: Optional[float] = None, unrealized: Optional[float] = None):
        ts = time.time()
        row = (
            ts,
            float(equity),
            float(cash),
            float(realized_total) if realized_total is not None else None,
            float(unrealized) if unrealized is not None else None,
        )
        with self._connect() as conn:
            c = conn.cursor()
            c.execute(
                """
                INSERT INTO equity (ts, equity, cash, realized_total, unrealized)
                VALUES (?,?,?,?,?)
                """,
                row,
            )
            conn.commit()
