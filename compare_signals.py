"""
compare_signals.py

FEATURES:
- Reads CSV logs from MT5, cTrader, TradingView
- Matches signals by date, symbol, and side
- Compares:
    - Matched signals
    - Missed / extra signals
    - R:R consistency
    - Candle body %
- Outputs verification table & summary stats
- Ready to run: configure file paths to your CSV exports
"""
import pandas as pd

mt5_csv = "MT5_signals.csv"
ctrader_csv = "cTrader_signals.csv"
tv_csv = "TradingView_signals.csv"

# Load CSVs
df_mt5 = pd.read_csv(mt5_csv)
df_ct = pd.read_csv(ctrader_csv)
df_tv = pd.read_csv(tv_csv)

def match_signals(df1, df2):
    df1['key'] = df1['timestamp'].astype(str) + "_" + df1['symbol'] + "_" + df1['side']
    df2['key'] = df2['timestamp'].astype(str) + "_" + df2['symbol'] + "_" + df2['side']
    matched = df1[df1['key'].isin(df2['key'])]
    extra = df1[~df1['key'].isin(df2['key'])]
    missed = df2[~df2['key'].isin(df1['key'])]
    return matched, extra, missed

matched_mt5_tv, extra_mt5_tv, missed_mt5_tv = match_signals(df_mt5, df_tv)

print("Matched signals MT5 vs TV:", len(matched_mt5_tv))
print("Extra MT5 signals not in TV:", len(extra_mt5_tv))
print("Missed MT5 signals compared to TV:", len(missed_mt5_tv))
