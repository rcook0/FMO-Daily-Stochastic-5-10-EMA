"""
compare_logs.py - Compare EOD strategy signals across platforms
"""

import pandas as pd

def compare_signals(py_csv, mt5_csv=None, ctrader_csv=None):
    df_py = pd.read_csv(py_csv)
    out = {"python": len(df_py)}

    if mt5_csv:
        df_mt5 = pd.read_csv(mt5_csv)
        merged = df_py.merge(df_mt5, on=["timestamp","symbol","side"], suffixes=("_py","_mt5"))
        out["matched_mt5"] = len(merged)
        out["extra_py_vs_mt5"] = len(df_py) - len(merged)
        out["extra_mt5_vs_py"] = len(df_mt5) - len(merged)

    if ctrader_csv:
        df_ct = pd.read_csv(ctrader_csv)
        merged = df_py.merge(df_ct, on=["timestamp","symbol","side"], suffixes=("_py","_ct"))
        out["matched_ct"] = len(merged)
        out["extra_py_vs_ct"] = len(df_py) - len(merged)
        out["extra_ct_vs_py"] = len(df_ct) - len(merged)

    return out
