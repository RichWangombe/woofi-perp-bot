import time
from pathlib import Path

import pandas as pd
import streamlit as st
import sqlite3

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = PROJECT_ROOT / "logs"
TRADES_CSV = LOGS_DIR / "trades.csv"
EQUITY_CSV = LOGS_DIR / "equity.csv"
SQLITE_DB = LOGS_DIR / "trading.db"
REFRESH_SEC = 3

st.set_page_config(page_title="WOOFi Perp Bot Dashboard", layout="wide")
st.title("WOOFi Perp Bot Dashboard")
st.caption("Live view of paper/backtest runs. Make sure the bot is running in another terminal.")

colA, colB, colC, colD = st.columns(4)


@st.cache_data(ttl=2)
def load_equity():
    # SQLite preferred if available
    if SQLITE_DB.exists():
        try:
            conn = sqlite3.connect(SQLITE_DB.as_posix())
            df = pd.read_sql_query("SELECT * FROM equity ORDER BY ts ASC", conn)
            conn.close()
            if not df.empty:
                df["ts"] = pd.to_datetime(df["ts"], unit="s")
            return df
        except Exception:
            pass
    if EQUITY_CSV.exists():
        df = pd.read_csv(EQUITY_CSV)
        if not df.empty:
            df["ts"] = pd.to_datetime(df["ts"], unit="s")
        return df
    return pd.DataFrame(columns=["ts", "equity", "cash"])  # empty


@st.cache_data(ttl=2)
def load_trades(n: int = 200):
    # SQLite preferred if available
    if SQLITE_DB.exists():
        try:
            conn = sqlite3.connect(SQLITE_DB.as_posix())
            df = pd.read_sql_query(f"SELECT * FROM trades ORDER BY ts DESC LIMIT {int(n)}", conn)
            conn.close()
            if not df.empty:
                df["ts"] = pd.to_datetime(df["ts"], unit="s")
            return df
        except Exception:
            pass
    if TRADES_CSV.exists():
        df = pd.read_csv(TRADES_CSV)
        if not df.empty:
            df["ts"] = pd.to_datetime(df["ts"], unit="s")
            df = df.sort_values("ts", ascending=False).head(n)
        return df
    return pd.DataFrame(columns=["ts","symbol","side","price","qty_quote","fee","equity","cash"])  # empty


def summary_metrics(eq_df: pd.DataFrame):
    if eq_df.empty:
        colA.metric("Equity", "—")
        colB.metric("Cash", "—")
        colC.metric("Unrealized", "—")
        colD.metric("Realized", "—")
        return
    start_eq = eq_df["equity"].iloc[0]
    last_eq = eq_df["equity"].iloc[-1]
    last_cash = eq_df["cash"].iloc[-1]
    last_unreal = eq_df.get("unrealized", pd.Series([0])).iloc[-1]
    last_real = eq_df.get("realized_total", pd.Series([0])).iloc[-1]
    colA.metric("Equity", f"{last_eq:,.2f} USD")
    colB.metric("Cash", f"{last_cash:,.2f} USD")
    colC.metric("Unrealized", f"{last_unreal:+,.2f} USD")
    colD.metric("Realized", f"{last_real:+,.2f} USD")


def equity_chart(eq_df: pd.DataFrame):
    st.subheader("Equity Curve")
    if eq_df.empty:
        st.info("No equity data yet. Start the bot to generate logs/equity.csv.")
        return
    chart_df = eq_df.set_index("ts")["equity"]
    st.line_chart(chart_df)


def trades_table(trades_df: pd.DataFrame):
    st.subheader("Recent Trades")
    if trades_df.empty:
        st.info("No trade data yet. Start the bot to generate logs/trades.csv.")
        return
    cols = [
        "ts","symbol","side","price","qty_quote","fee",
        "realized_delta","realized_total","unrealized",
        "equity_after","cash_after","pos_qty","pos_avg"
    ]
    show = trades_df[[c for c in cols if c in trades_df.columns]].copy()
    show.rename(columns={"ts": "Time", "qty_quote": "Qty (quote)"}, inplace=True)
    st.dataframe(show, use_container_width=True, hide_index=True)


def compute_trade_metrics(trades_df: pd.DataFrame):
    if trades_df.empty or "realized_delta" not in trades_df.columns:
        return {"win_rate": None, "avg_win": None, "avg_loss": None}
    realized = trades_df[trades_df["realized_delta"].notna()]["realized_delta"]
    realized = realized[realized != 0]
    if realized.empty:
        return {"win_rate": None, "avg_win": None, "avg_loss": None}
    wins = realized[realized > 0]
    losses = realized[realized < 0]
    win_rate = len(wins) / (len(wins) + len(losses)) if (len(wins) + len(losses)) > 0 else None
    avg_win = wins.mean() if not wins.empty else None
    avg_loss = losses.mean() if not losses.empty else None
    return {"win_rate": win_rate, "avg_win": avg_win, "avg_loss": avg_loss}


def max_drawdown(eq_df: pd.DataFrame):
    if eq_df.empty:
        return None
    s = eq_df["equity"]
    roll_max = s.cummax()
    dd = (s - roll_max) / roll_max
    return float(dd.min()) if not dd.empty else None


def exposure_estimate(trades_df: pd.DataFrame):
    if trades_df.empty:
        return 0.0
    # Take latest per symbol pos_qty and price
    latest = trades_df.sort_values("ts").groupby("symbol").tail(1)
    latest = latest.dropna(subset=["pos_qty"]) if "pos_qty" in latest.columns else latest
    if latest.empty or "pos_qty" not in latest.columns:
        return 0.0
    latest["exposure"] = latest["pos_qty"].abs() * latest["price"].abs()
    return float(latest["exposure"].sum())


def last_prices(trades_df: pd.DataFrame):
    if trades_df.empty:
        return {}
    latest = trades_df.sort_values("ts").groupby("symbol").tail(1)
    out = {}
    for _, row in latest.iterrows():
        out[str(row.get("symbol"))] = float(row.get("price")) if row.get("price") is not None else None
    return out


eq_df = load_equity()
tr_df = load_trades()

summary_metrics(eq_df)

stats = compute_trade_metrics(tr_df)
md = max_drawdown(eq_df)
exp_usd = exposure_estimate(tr_df)
marks = last_prices(tr_df)

col1, col2, col3 = st.columns(3)
col1.metric("Win Rate", f"{stats['win_rate']*100:.1f}%" if stats["win_rate"] is not None else "—")
col2.metric("Avg Win", f"{stats['avg_win']:+.2f}" if stats["avg_win"] is not None else "—")
col3.metric("Avg Loss", f"{stats['avg_loss']:+.2f}" if stats["avg_loss"] is not None else "—")

col4, col5 = st.columns(2)
col4.metric("Max Drawdown", f"{md*100:.2f}%" if md is not None else "—")
col5.metric("Est. Exposure", f"{exp_usd:,.2f} USD")

if marks:
    st.write("Last Prices: ", ", ".join([f"{k}: {v:,.2f}" for k, v in marks.items() if v is not None]))

tab1, tab2 = st.tabs(["Overview", "Judge View"])
with tab1:
    left, right = st.columns([2, 1])
    with left:
        equity_chart(eq_df)
    with right:
        trades_table(tr_df)
with tab2:
    st.subheader("Judge View")
    # Compact top metrics
    colA2, colB2, colC2, colD2 = st.columns(4)
    summary_metrics(eq_df)
    col1b, col2b, col3b = st.columns(3)
    col1b.metric("Win Rate", f"{stats['win_rate']*100:.1f}%" if stats["win_rate"] is not None else "—")
    col2b.metric("Avg Win", f"{stats['avg_win']:+.2f}" if stats["avg_win"] is not None else "—")
    col3b.metric("Avg Loss", f"{stats['avg_loss']:+.2f}" if stats["avg_loss"] is not None else "—")
    st.divider()
    equity_chart(eq_df)
    trades_table(tr_df.head(20))

# Sidebar auto-refresh controls
st.sidebar.subheader("Refresh")
auto = st.sidebar.checkbox("Auto-refresh", value=True)
interval = st.sidebar.slider("Refresh every (sec)", 2, 30, REFRESH_SEC)

st.caption(f"Auto-refresh: {'ON' if auto else 'OFF'}")
if auto:
    time.sleep(interval)
    st.rerun()
