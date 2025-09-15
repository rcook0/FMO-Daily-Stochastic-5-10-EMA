"""
simulator.py - Trade simulator for multiple strategies (EOD, Core, etc.)
"""
import pandas as pd
import numpy as np

def simulate_positions(signals: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    """
    Simulate trades given signals + OHLCV price data.

    signals: DataFrame with at least ['timestamp','side','entry','stop','tp']
    prices : OHLCV DataFrame (DatetimeIndex, cols: open, high, low, close)

    Returns: signals with outcome columns:
      ['exit_price','exit_reason','PnL','R_mult']
    """

    if not isinstance(prices.index, pd.DatetimeIndex):
        if "timestamp" in prices.columns:
            prices = prices.copy()
            prices["timestamp"] = pd.to_datetime(prices["timestamp"], utc=True, errors="coerce")
            prices = prices.set_index("timestamp").sort_index()
        else:
            raise ValueError("prices must have a DatetimeIndex or a 'timestamp' column")

    results = []
    for _, s in signals.iterrows():
        side = s["side"].upper()
        entry = float(s["entry"])
        stop  = float(s["stop"])
        tp    = float(s.get("tp", np.nan))
        ts    = pd.to_datetime(s["timestamp"], utc=True)

        # Price data from entry timestamp onwards
        future = prices.loc[ts:]
        exit_price, exit_reason = None, None

        for t, row in future.iterrows():
            hi, lo = float(row["high"]), float(row["low"])
            if side == "BUY":
                if lo <= stop:
                    exit_price, exit_reason = stop, "SL"; break
                if not np.isnan(tp) and hi >= tp:
                    exit_price, exit_reason = tp, "TP"; break
            elif side == "SELL":
                if hi >= stop:
                    exit_price, exit_reason = stop, "SL"; break
                if not np.isnan(tp) and lo <= tp:
                    exit_price, exit_reason = tp, "TP"; break

        if exit_price is None:
            exit_price, exit_reason = float(future.iloc[-1]["close"]), "Open"

        pl = (exit_price - entry) * (1 if side == "BUY" else -1)
        R  = float(s.get("R", np.nan))
        r_mult = pl / R if R and not np.isnan(R) else np.nan

        res = s.to_dict()
        res.update({"exit_price": exit_price,
                    "exit_reason": exit_reason,
                    "PnL": pl,
                    "R_mult": r_mult})
        results.append(res)

    return pd.DataFrame(results)
