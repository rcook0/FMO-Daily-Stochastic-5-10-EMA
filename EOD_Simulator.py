"""
simulator.py - Simple trade simulator for EOD Continuation Strategy
"""

import pandas as pd

def simulate_positions(signals: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    """
    Simulate entry, SL/TP, and exit of signals.
    - signals: DataFrame from run_strategy_on_dataframe()
    - prices:  OHLCV DataFrame with same datetime index
    Returns signals with simulated outcome columns.
    """
    results = []
    for _, s in signals.iterrows():
        side = s["side"]
        entry = s["entry"]
        stop  = s["stop"]
        tp    = s["tp"]
        ts    = s["timestamp"]

        # search forward in prices until exit
        future = prices.loc[ts:]
        exit_price, exit_reason = None, None

        for t, row in future.iterrows():
            if side == "BUY":
                if row["low"] <= stop:
                    exit_price, exit_reason = stop, "SL"
                    break
                if row["high"] >= tp:
                    exit_price, exit_reason = tp, "TP"
                    break
            else:
                if row["high"] >= stop:
                    exit_price, exit_reason = stop, "SL"
                    break
                if row["low"] <= tp:"""
simulator.py - Simple trade simulator for EOD Continuation Strategy
"""

import pandas as pd

def simulate_positions(signals: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    """
    Simulate entry, SL/TP, and exit of signals.
    - signals: DataFrame from run_strategy_on_dataframe()
    - prices:  OHLCV DataFrame with same datetime index
    Returns signals with simulated outcome columns.
    """
    results = []
    for _, s in signals.iterrows():
        side = s["side"]
        entry = s["entry"]
        stop  = s["stop"]
        tp    = s["tp"]
        ts    = s["timestamp"]

        # search forward in prices until exit
        future = prices.loc[ts:]
        exit_price, exit_reason = None, None

        for t, row in future.iterrows():
            if side == "BUY":
                if row["low"] <= stop:
                    exit_price, exit_reason = stop, "SL"
                    break
                if row["high"] >= tp:
                    exit_price, exit_reason = tp, "TP"
                    break
            else:
                if row["high"] >= stop:
                    exit_price, exit_reason = stop, "SL"
                    break
                if row["low"] <= tp:
                    exit_price, exit_reason = tp, "TP"
                    break

        if exit_price is None:
            exit_price, exit_reason = future.iloc[-1]["close"], "Open"

        pl = (exit_price - entry) * (1 if side=="BUY" else -1)
        r_mult = pl / s["R"] if s["R"]>0 else None

        res = s.to_dict()
        res.update({"exit_price": exit_price, "exit_reason": exit_reason, "PnL": pl, "R_mult": r_mult})
        results.append(res)

    return pd.DataFrame(results)

                    exit_price, exit_reason = tp, "TP"
                    break

        if exit_price is None:
            exit_price, exit_reason = future.iloc[-1]["close"], "Open"

        pl = (exit_price - entry) * (1 if side=="BUY" else -1)
        r_mult = pl / s["R"] if s["R"]>0 else None

        res = s.to_dict()
        res.update({"exit_price": exit_price, "exit_reason": exit_reason, "PnL": pl, "R_mult": r_mult})
        results.append(res)

    return pd.DataFrame(results)
