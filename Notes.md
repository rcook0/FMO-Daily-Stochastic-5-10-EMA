Three ready-to-use code implementations / starters you can drop into the platform editors and run or extend. 
Each implementation follows the same core rules: 
5 EMA vs 10 EMA trend filter, 
Stochastic confirmation, p
rice near S/R zones, and 
signals are generated at the daily close.

Each script can be used as signal-only (you receive alerts) or auto-execute (MT5 / cTrader).


What’s included:

TradingView Pine Script v5 — daily strategy/script that can be used as both indicator (alerts) and strategy (backtest). It detects S/R automatically using pivot highs/lows and allows manual S/R overrides. Alerts fire at daily close.

MT5 (MQL5) EA — daily EA that can run on any chart (uses the daily timeframe internally); supports auto-execution, fixed SR inputs (up to 4 levels), position sizing by % equity, SL/TP and basic trade management.

cTrader cBot (C#) — equivalent cBot for cTrader Automate: daily-check logic, manual SR inputs, percent-based sizing, SL/TP, and easy toggles for alerts/automated entry.



Notes / assumptions (so you know what code does):

All scripts operate on daily timeframe logic and evaluate conditions at the close of the daily candle. That matches your end-of-day workflow (London/NY close).

S/R detection: automatic pivot-based detection is included for TradingView (configurable pivot lengths). For MT5 and cTrader I added inputs for up to four manual S/R price levels (many traders prefer manually-drawn S/R for daily charts). You can extend to auto-detect in those platforms later.

Stochastic default: 14, 3, 3 (configurable). Signal requires %K crossing %D in the expected direction (from oversold for buys, from overbought for sells).

EMA rule: 5 EMA above 10 EMA = bullish bias (buy setups only); 5 < 10 = bearish bias (sell setups only). You can set allowCounterTrend = true if you want both.

Risk sizing: percent-of-equity or fixed lots/volume supported (MT5 & cTrader). Default is 1% risk per trade; EA/cBot will compute lot size to match SL risk.

The code is conservative — uses checks for existing positions (to avoid duplicates) and provides toggles for autoTrade vs signalOnly.


1. Signal Logic (shared core across platforms)

Timeframe: Daily close (you only need to check after 9–10pm London).

Trend filter:

Bullish bias if 5 EMA > 10 EMA.

Bearish bias if 5 EMA < 10 EMA.

Momentum check: Stochastic %K crosses %D from OB/OS zones.

Price location: Within tolerance of a daily S/R (manual list or ATR-based zone).

2. Trade Management Hints (output in alert/log, not auto-applied)

When a valid setup triggers, the system prints/logs something like:

Bias: “Bullish setup (5>10 EMA, Stoch rising).”

Entry zone: “Near daily support at 1920 (within 0.5% / 20 pips).”

Stop hint: “Place SL below 1910 (ATR-based).”

TP hint: “Next resistance 1950. R:R ≈ 2.1.”

Risk note: “Max risk 1–2% recommended. Position size = 0.45 lots (equity-based).”

Management options:

At +1R → partial close / move SL to breakeven.

Trail below 10 EMA (for trend continuation).

Full exit at opposite daily S/R.

3. Platform specifics

MT5 (Indicator + Panel)

Arrows on chart + alert popup at daily close.

Panel shows trade hints (bias, SL/TP levels, R:R).

Optional lot size calculator based on your % equity rule.

No auto entry.

cTrader (cBot “advisor”)

Runs on daily timeframe.

Prints log + message (optionally Telegram/Discord).

Shows suggested levels but leaves trade to you.

TradingView Pine (study, not strategy)

Plots arrows + highlights when conditions align near S/R.

Alerts you at/after daily candle close.

Uses either manual horizontal lines (drawn S/R) or ATR proxy.

No backtest reliance (just forward signals).
