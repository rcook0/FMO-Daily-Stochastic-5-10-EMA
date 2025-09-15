# EOD Continuation Strategy (Python)

Pure Python implementation of the End-of-Day Continuation Strategy.

## Features
- End-of-day evaluation (22:30 London)
- Strong candle filter
- Stochastic (14,3,3) baseline
- Entry/Stop above/below prior candle
- Optional EMA trend filter
- Manual exit hint on opposite Stoch cross
- Simulator: SL/TP + R-multiple outcomes
- Comparator: match Python vs MT5/cTrader signals
- Jupyter notebook demo

## Quickstart
```bash
pip install pandas matplotlib
python eod_continuation.py sample_data.csv --symbol XAUUSD
