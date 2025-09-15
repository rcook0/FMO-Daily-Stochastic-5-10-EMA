#!/usr/bin/env python3
"""
EOD Continuation Strategy (Pure Python)

Features
--------
- End-of-day evaluation (default 22:30 Europe/London)
- Strong candle filter (body >= body_min_pct% of range, aligned with direction)
- Stochastic (k_len=14, k_smooth=3, d_smooth=3):
    * Long setup: %K >= stoch_baseline (default 50)
    * Short setup: %K <= 100 - stoch_baseline (default 50 -> <= 50)
- Entry/Stop from prior daily candle range with buffer:
    * Long: entry = high_prev + buffer, stop = low_prev - buffer
    * Short: entry = low_prev - buffer,  stop = high_prev + buffer
- Exit hint (manual): opposite Stochastic %K/%D crossover.
- Optional EMA(5/10) trend filter (default off).
- Modular API + CLI to read CSV and emit signals CSV.

Usage
-----
# As a script:
python eod_continuation.py data.csv --symbol XAUUSD --out signals.csv

# As a module:
from eod_continuation import StrategyConfig, run_strategy_on_dataframe
signals_df = run_strategy_on_dataframe(df, StrategyConfig())

Notes
-----
- This is signal preparation. Order placement/position tracking is out of scope.
- Timezone check prevents signal generation unless current time >= cut-off (configurable).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import Optional, Tuple

import numpy as np
import pandas as pd

try:
    # Python 3.9+
    from zoneinfo import ZoneInfo
except ImportError:
    # Fallback; if not available, we skip tz enforcement
    ZoneInfo = None  # type: ignore


# --------------------------- Config ---------------------------

@dataclass
class StrategyConfig:
    symbol: str = "XAUUSD"
    # Stochastic parameters
    stoch_k_len: int = 14
    stoch_k_smooth: int = 3
    stoch_d_smooth: int = 3
    stoch_baseline: float = 50.0  # baseline for %K threshold
    # Candle strength
    use_candle_strength: bool = True
    body_min_pct: float = 50.0  # body >= X% of range
    # Entry/Stop buffer (same units as price; e.g., 0.50 for gold if your prices are 1-decimal pips)
    buffer: float = 0.00
    # EMA trend filter (optional)
    use_ema_filter: bool = False
    ema_fast: int = 5
    ema_slow: int = 10
    # TP as R multiple (optional guidance column)
    tp_r_multiple: float = 2.0
    # Evaluation gate
    london_cutoff_hhmm: Tuple[int, int] = (22, 30)  # 22:30 London
    london_tz: str = "Europe/London"
    # Require proximity to session close day? (we already gate by time; this flag kept for extension)
    require_cutoff: bool = True


# ---------------------- Indicator utils ----------------------

def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()

def stochastic_kd(
    highs: pd.Series,
    lows: pd.Series,
    closes: pd.Series,
    k_len: int = 14,
    k_smooth: int = 3,
    d_smooth: int = 3,
) -> Tuple[pd.Series, pd.Series]:
    """
    Returns (%K, %D) in 0..100.
    """
    ll = lows.rolling(k_len, min_periods=k_len).min()
    hh = highs.rolling(k_len, min_periods=k_len).max()
    # Avoid division by zero
    rng = (hh - ll).replace(0, np.nan)
    k = (closes - ll) / rng * 100.0
    k = k.rolling(k_smooth, min_periods=k_smooth).mean()
    d = k.rolling(d_smooth, min_periods=d_smooth).mean()
    return k, d


def strong_candle_mask(
    opens: pd.Series,
    highs: pd.Series,
    lows: pd.Series,
    closes: pd.Series,
    body_min_pct: float,
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Returns (strong_bull, strong_bear, body_pct).
    strong_bull: close>open & body%>=threshold
    strong_bear: close<open & body%>=threshold
    """
    rng = (highs - lows).replace(0, np.nan)
    body = (closes - opens).abs()
    body_pct = (body / rng) * 100.0
    strong_bull = (closes > opens) & (body_pct >= body_min_pct)
    strong_bear = (closes < opens) & (body_pct >= body_min_pct)
    return strong_bull.fillna(False), strong_bear.fillna(False), body_pct.fillna(0.0)


def stoch_cross(sign_up: bool, k_prev: float, d_prev: float, k_now: float, d_now: float) -> bool:
    """
    True if %K/%D cross in desired direction.
    sign_up=True  -> cross up  (k_prev<d_prev & k_now>d_now)
    sign_up=False -> cross down(k_prev>d_prev & k_now<d_now)
    """
    if any(map(pd.isna, [k_prev, d_prev, k_now, d_now])):
        return False
    return (k_prev < d_prev and k_now > d_now) if sign_up else (k_prev > d_prev and k_now < d_now)


# ---------------------- Time gate (London) ----------------------

def past_cutoff_now(london_hhmm: Tuple[int, int], tz_name: str) -> bool:
    """
    Returns True if current time in London >= cutoff hh:mm.
    If zoneinfo not available, returns True (do not block).
    """
    if ZoneInfo is None:
        return True
    try:
        now_london = datetime.now(ZoneInfo(tz_name))
        cutoff = time(london_hhmm[0], london_hhmm[1], tzinfo=ZoneInfo(tz_name))
        return now_london.timetz() >= cutoff
    except Exception:
        return True


# ---------------------- Core strategy ----------------------

def run_strategy_on_dataframe(df: pd.DataFrame, cfg: StrategyConfig) -> pd.DataFrame:
    """
    EOD Continuation Strategy on a daily OHLCV dataframe.
    Returns a dataframe of signals (one row per bar) with:
      ['timestamp','symbol','side','entry','stop','tp','body_pct','k','d','exit_hint']
    Notes:
    - Signals are based on the *previous closed bar*; entries/stops reference that bar's range.
    - Exit hints are opposite stoch crossovers (for manual management).
    """
    # Defensive copy
    df = df.copy()

    # Basic sanity
    required = {"open", "high", "low", "close"}
    missing = required - set(map(str.lower, df.columns))
    # Normalize column names (case-insensitive mapping)
    df.columns = [c.lower() for c in df.columns]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Input DataFrame missing required column: '{col}'")

    # Indicators
    if cfg.use_ema_filter:
        df["ema_fast"] = ema(df["close"], cfg.ema_fast)
        df["ema_slow"] = ema(df["close"], cfg.ema_slow)

    df["k"], df["d"] = stochastic_kd(
        df["high"], df["low"], df["close"],
        k_len=cfg.stoch_k_len,
        k_smooth=cfg.stoch_k_smooth,
        d_smooth=cfg.stoch_d_smooth,
    )

    strong_bull, strong_bear, body_pct = strong_candle_mask(
        df["open"], df["high"], df["low"], df["close"], cfg.body_min_pct
    )
    df["body_pct"] = body_pct

    # Prepare result rows
    rows = []

    # We reference prior day's *closed* candle for entry/stop – start at index 1
    for i in range(1, len(df)):
        ts = df.index[i] if isinstance(df.index, pd.DatetimeIndex) else pd.to_datetime(i)
        o_prev = df["open"].iloc[i - 1]
        h_prev = df["high"].iloc[i - 1]
        l_prev = df["low"].iloc[i - 1]
        c_prev = df["close"].iloc[i - 1]
        k_prev = df["k"].iloc[i - 1]
        d_prev = df["d"].iloc[i - 1]

        # Current bar stoch (used for crossover evaluation at i-th bar close)
        k_now = df["k"].iloc[i]
        d_now = df["d"].iloc[i]

        # Strong candle flag on the *closed* bar
        bull_ok = bool(strong_bull.iloc[i - 1]) if cfg.use_candle_strength else True
        bear_ok = bool(strong_bear.iloc[i - 1]) if cfg.use_candle_strength else True

        # Stochastic baseline filter on *closed* bar
        k_ok_long = (k_prev >= cfg.stoch_baseline)
        k_ok_short = (k_prev <= (100.0 - cfg.stoch_baseline))

        # Optional EMA filter
        ema_ok_long = True
        ema_ok_short = True
        if cfg.use_ema_filter:
            ema_fast_prev = df["ema_fast"].iloc[i - 1]
            ema_slow_prev = df["ema_slow"].iloc[i - 1]
            ema_ok_long = bool(ema_fast_prev > ema_slow_prev)
            ema_ok_short = bool(ema_fast_prev < ema_slow_prev)

        # Construct entry/stop from prior bar range + buffer
        entry_long = h_prev + cfg.buffer
        stop_long  = l_prev - cfg.buffer
        entry_short = l_prev - cfg.buffer
        stop_short  = h_prev + cfg.buffer

        # Long & Short setup conditions (at prior close)
        long_setup  = bull_ok  and k_ok_long  and ema_ok_long
        short_setup = bear_ok  and k_ok_short and ema_ok_short

        # Exit hints (for an open position managed manually):
        # If in long, exit when %K crosses *below* %D. If in short, exit when %K crosses *above* %D.
        long_exit_hint  = stoch_cross(False, k_prev, d_prev, k_now, d_now)  # cross DOWN
        short_exit_hint = stoch_cross(True,  k_prev, d_prev, k_now, d_now)  # cross UP

        if long_setup:
            R = max(entry_long - stop_long, 0.0)
            tp = entry_long + cfg.tp_r_multiple * R if R > 0 else np.nan
            rows.append({
                "timestamp": ts,
                "symbol": cfg.symbol,
                "side": "BUY",
                "ref_bar_close": c_prev,
                "entry": entry_long,
                "stop": stop_long,
                "tp": tp,
                "R": R,
                "body_pct": float(df["body_pct"].iloc[i - 1]),
                "k": float(k_prev) if pd.notna(k_prev) else np.nan,
                "d": float(d_prev) if pd.notna(d_prev) else np.nan,
                "exit_hint": bool(long_exit_hint),
            })

        if short_setup:
            R = max(stop_short - entry_short, 0.0)
            tp = entry_short - cfg.tp_r_multiple * R if R > 0 else np.nan
            rows.append({
                "timestamp": ts,
                "symbol": cfg.symbol,
                "side": "SELL",
                "ref_bar_close": c_prev,
                "entry": entry_short,
                "stop": stop_short,
                "tp": tp,
                "R": R,
                "body_pct": float(df["body_pct"].iloc[i - 1]),
                "k": float(k_prev) if pd.notna(k_prev) else np.nan,
                "d": float(d_prev) if pd.notna(d_prev) else np.nan,
                "exit_hint": bool(short_exit_hint),
            })

    out = pd.DataFrame(rows)
    # Enforce evaluation time gate (optional)
    if cfg.require_cutoff and len(out) > 0 and ZoneInfo is not None:
        if not past_cutoff_now(cfg.london_cutoff_hhmm, cfg.london_tz):
            # If before cutoff, you might choose to return empty or mark as 'pending'
            out["pending_until"] = f"{cfg.london_cutoff_hhmm[0]:02d}:{cfg.london_cutoff_hhmm[1]:02d} {cfg.london_tz}"
    return out


# ---------------------------- CLI ----------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="EOD Continuation Strategy (pure Python)")
    p.add_argument("csv", help="Input CSV with columns: timestamp,open,high,low,close[,volume]")
    p.add_argument("--symbol", default="XAUUSD")
    p.add_argument("--out", default="eod_signals.csv", help="Output signals CSV")
    p.add_argument("--body", type=float, default=50.0, help="Min body %% of range")
    p.add_argument("--buffer", type=float, default=0.00, help="Entry/Stop buffer (price units)")
    p.add_argument("--stoch_k", type=int, default=14)
    p.add_argument("--stoch_k_smooth", type=int, default=3)
    p.add_argument("--stoch_d", type=int, default=3)
    p.add_argument("--stoch_base", type=float, default=50.0)
    p.add_argument("--ema_filter", action="store_true", help="Enable EMA(5/10) trend filter")
    p.add_argument("--ema_fast", type=int, default=5)
    p.add_argument("--ema_slow", type=int, default=10)
    p.add_argument("--tp_r", type=float, default=2.0)
    p.add_argument("--cutoff", default="22:30", help="London cutoff HH:MM")
    p.add_argument("--no_cutoff_gate", action="store_true", help="Do not enforce cutoff gate")
    return p.parse_args()

def _load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    # best-effort timestamp parse
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        df = df.set_index("timestamp")
    else:
        # assume index is date
        df.index = pd.to_datetime(df.index, utc=True, errors="coerce")
    df = df.sort_index()
    return df

def main():
    args = _parse_args()
    hh, mm = map(int, args.cutoff.split(":"))
    cfg = StrategyConfig(
        symbol=args.symbol,
        stoch_k_len=args.stoch_k,
        stoch_k_smooth=args.stoch_k_smooth,
        stoch_d_smooth=args.stoch_d,
        stoch_baseline=args.stoch_base,
        use_candle_strength=True,
        body_min_pct=args.body,
        buffer=args.buffer,
        use_ema_filter=args.ema_filter,
        ema_fast=args.ema_fast,
        ema_slow=args.ema_slow,
        tp_r_multiple=args.tp_r,
        london_cutoff_hhmm=(hh, mm),
        require_cutoff=not args.no_cutoff_gate,
    )
    df = _load_csv(args.csv)
    signals = run_strategy_on_dataframe(df, cfg)
    signals.to_csv(args.out, index=False)
    print(f"Wrote {len(signals)} signals to {args.out}")

if __name__ == "__main__":
    main()
