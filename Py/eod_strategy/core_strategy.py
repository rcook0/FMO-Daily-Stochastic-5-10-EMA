"""
core_strategy.py - Core Strategy (Financial Markets Online)
Daily chart, EMA stack + RSI confirmation.
"""

import pandas as pd
import numpy as np

def run_core_strategy(df: pd.DataFrame,
                      rsi_len: int = 14,
                      ema_periods=(20, 50, 100),
                      tp_r_multiple: float = 2.0) -> pd.DataFrame:
    """
    Core Strategy logic.
    Returns a DataFrame of signals:
      ['timestamp','side','entry','stop','tp','rsi','ema20','ema50','ema100']
    """

    df = df.copy()
    df.columns = [c.lower() for c in df.columns]
    if not isinstance(df.index, pd.DatetimeIndex):
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
            df = df.set_index("timestamp")
        else:
            raise ValueError("DataFrame must have datetime index or 'timestamp' column.")

    # EMAs
    ema20, ema50, ema100 = [df["close"].ewm(span=p, adjust=False).mean() for p in ema_periods]
    df["ema20"], df["ema50"], df["ema100"] = ema20, ema50, ema100

    # RSI
    delta = df["close"].diff()
    up = delta.clip(lower=0)
    down = -1*delta.clip(upper=0)
    roll_up = up.ewm(span=rsi_len, adjust=False).mean()
    roll_down = down.ewm(span=rsi_len, adjust=False).mean()
    rs = roll_up / roll_down.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))

    rows = []
    for i in range(1, len(df)):
        ts = df.index[i]
        c = df["close"].iloc[i]
        ema20_i, ema50_i, ema100_i = df["ema20"].iloc[i], df["ema50"].iloc[i], df["ema100"].iloc[i]
        rsi_i = df["rsi"].iloc[i]

        # Bias check
        long_bias = ema20_i > ema50_i > ema100_i
        short_bias = ema20_i < ema50_i < ema100_i

        # Signal
        if long_bias and rsi_i > 50:
            entry, stop = c, ema20_i
            R = entry - stop
            tp = entry + tp_r_multiple * R if R > 0 else np.nan
            rows.append({"timestamp": ts, "side": "BUY", "entry": entry, "stop": stop, "tp": tp,
                         "rsi": rsi_i, "ema20": ema20_i, "ema50": ema50_i, "ema100": ema100_i})

        if short_bias and rsi_i < 50:
            entry, stop = c, ema20_i
            R = stop - entry
            tp = entry - tp_r_multiple * R if R > 0 else np.nan
            rows.append({"timestamp": ts, "side": "SELL", "entry": entry, "stop": stop, "tp": tp,
                         "rsi": rsi_i, "ema20": ema20_i, "ema50": ema50_i, "ema100": ema100_i})

    return pd.DataFrame(rows)
