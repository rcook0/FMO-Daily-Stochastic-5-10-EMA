"""
backtest_all.py - Run all strategies in the package on a dataset and emit consolidated metrics.
Supports single CSV or YAML config for batch runs, with plots and HTML report.
Generates a batch_index.html when using YAML configs, with aggregate equity curves.
"""
import os
import argparse
import pandas as pd
import numpy as np
import yaml
import matplotlib.pyplot as plt
import base64

from .eod_continuation import StrategyConfig, run_strategy_on_dataframe
from .core_strategy import run_core_strategy
from .simulator import simulate_positions

def calc_metrics(results: pd.DataFrame) -> dict:
    if results is None or len(results) == 0:
        return {"trades": 0, "win_rate": 0.0, "avg_r": 0.0, "total_r": 0.0, "max_dd": 0.0}
    n = len(results)
    win_rate = (results["exit_reason"] == "TP").mean() if n > 0 else 0.0
    avg_r = float(results["R_mult"].mean())
    total_r = float(results["R_mult"].sum())
    cum_r = results["R_mult"].cumsum()
    max_dd = float((cum_r.cummax() - cum_r).max())
    return {
        "trades": int(n),
        "win_rate": round(win_rate * 100, 2),
        "avg_r": round(avg_r, 3),
        "total_r": round(total_r, 3),
        "max_dd": round(max_dd, 3)
    }

def load_prices(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        df = df.set_index("timestamp")
    else:
        df.index = pd.to_datetime(df.index, utc=True, errors="coerce")
    df = df.sort_index()
    df.columns = [c.lower() for c in df.columns]
    return df

def _embed_image(path):
    if not os.path.exists(path):
        return "<p>No image available</p>"
    with open(path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode("utf-8")
    return f'<img src="{os.path.basename(path)}" style="max-width:800px;">'

def write_html_report(symbol, outdir, metrics_df):
    html_path = os.path.join(outdir, f"{symbol}_report.html")
    equity_img = os.path.join(outdir, f"{symbol}_equity_curve.png")
    metrics_img = os.path.join(outdir, f"{symbol}_metrics.png")

    html = f"""
    <html>
    <head><title>{symbol} Strategy Report</title></head>
    <body>
    <h1>{symbol} Strategy Report</h1>
    <h2>Metrics</h2>
    {metrics_df.to_html()}
    <h2>Equity Curve</h2>
    {_embed_image(equity_img)}
    <h2>Metrics Chart</h2>
    {_embed_image(metrics_img)}
    <h2>Downloads</h2>
    <ul>
        <li><a href="metrics_summary.csv">metrics_summary.csv</a></li>
        <li><a href="equity_curves.csv">equity_curves.csv</a></li>
        <li><a href="core_results.csv">core_results.csv</a></li>
        <li><a href="eod_results.csv">eod_results.csv</a></li>
    </ul>
    </body>
    </html>
    """
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    return html_path

def run_all(csv_path: str, symbol: str, outdir: str) -> str:
    os.makedirs(outdir, exist_ok=True)
    prices = load_prices(csv_path)

    # --- EOD Strategy ---
    eod_cfg = StrategyConfig(symbol=symbol)
    eod_signals = run_strategy_on_dataframe(prices, eod_cfg)
    eod_results = simulate_positions(eod_signals, prices)
    eod_metrics = calc_metrics(eod_results)
    eod_signals.to_csv(os.path.join(outdir, "eod_signals.csv"), index=False)
    eod_results.to_csv(os.path.join(outdir, "eod_results.csv"), index=False)

    # --- Core Strategy ---
    core_signals = run_core_strategy(prices)
    core_results = simulate_positions(core_signals, prices)
    core_metrics = calc_metrics(core_results)
    core_signals.to_csv(os.path.join(outdir, "core_signals.csv"), index=False)
    core_results.to_csv(os.path.join(outdir, "core_results.csv"), index=False)

    # Consolidated metrics
    metrics_df = pd.DataFrame([core_metrics, eod_metrics], index=["Core", "EOD"])
    metrics_path = os.path.join(outdir, "metrics_summary.csv")
    metrics_df.to_csv(metrics_path)

    # Equity curves
    curves = pd.DataFrame()
    if len(core_results) > 0:
        core_curve = core_results[["timestamp", "R_mult"]].copy()
        core_curve["core_cumR"] = core_curve["R_mult"].cumsum()
        curves = pd.merge(curves, core_curve[["timestamp","core_cumR"]], on="timestamp", how="outer") if not curves.empty else core_curve
    if len(eod_results) > 0:
        eod_curve = eod_results[["timestamp", "R_mult"]].copy()
        eod_curve["eod_cumR"] = eod_curve["R_mult"].cumsum()
        curves = pd.merge(curves, eod_curve[["timestamp","eod_cumR"]], on="timestamp", how="outer") if not curves.empty else eod_curve

    if not curves.empty:
        curves = curves.sort_values("timestamp")
        curves.to_csv(os.path.join(outdir, "equity_curves.csv"), index=False)

        # Plot equity curves
        plt.figure(figsize=(10,5))
        if "core_cumR" in curves:
            plt.plot(curves["timestamp"], curves["core_cumR"], label="Core")
        if "eod_cumR" in curves:
            plt.plot(curves["timestamp"], curves["eod_cumR"], label="EOD")
        plt.title(f"Cumulative R - {symbol}")
        plt.xlabel("Time")
        plt.ylabel("Cumulative R")
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(outdir, f"{symbol}_equity_curve.png"))
        plt.close()

        # Plot metrics bar chart
        metrics_df.T.plot(kind="bar", figsize=(8,4), title=f"Metrics - {symbol}")
        plt.tight_layout()
        plt.savefig(os.path.join(outdir, f"{symbol}_metrics.png"))
        plt.close()

    # HTML report
    write_html_report(symbol, outdir, metrics_df)

    return metrics_path

def run_from_config(config_path: str):
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)

    index_entries = []
    root_outdir = None

    for item in cfg.get("datasets", []):
        file = item["file"]
        symbol = item.get("symbol", "XAUUSD")
        outdir = item.get("outdir", f"reports/{symbol.lower()}")
        if root_outdir is None:
            root_outdir = os.path.dirname(outdir) if "/" in outdir else outdir
        print(f"Running backtest for {symbol} on {file}...")
        run_all(file, symbol, outdir)
        index_entries.append((symbol, outdir, f"{symbol}_report.html"))

    # Aggregate equity curves
    agg_df = None
    for symbol, outdir, _ in index_entries:
        curve_path = os.path.join(outdir, "equity_curves.csv")
        if os.path.exists(curve_path):
            df = pd.read_csv(curve_path, parse_dates=["timestamp"])
            df = df.set_index("timestamp")
            if agg_df is None:
                agg_df = df
            else:
                agg_df = agg_df.join(df, how="outer")

    all_curve_path = None
    if agg_df is not None and not agg_df.empty:
        agg_df = agg_df.sort_index().fillna(method="ffill")
        plt.figure(figsize=(10,6))
        for col in agg_df.columns:
            if col.endswith("cumR"):
                plt.plot(agg_df.index, agg_df[col], label=col)
        plt.title("Aggregate Equity Curves Across Symbols")
        plt.xlabel("Time")
        plt.ylabel("Cumulative R")
        plt.legend()
        all_curve_path = os.path.join(root_outdir, "all_equity_curves.png")
        plt.savefig(all_curve_path)
        plt.close()

    # Build master index
    if root_outdir:
        os.makedirs(root_outdir, exist_ok=True)
        index_path = os.path.join(root_outdir, "batch_index.html")
        with open(index_path, "w", encoding="utf-8") as f:
            f.write("<html><head><title>Batch Backtest Index</title></head><body>")
            f.write("<h1>Batch Backtest Reports</h1>")
            if all_curve_path:
                f.write("<h2>Aggregate Equity Curves</h2>")
                f.write(f'<img src="{os.path.basename(all_curve_path)}" style="max-width:900px;">')
            f.write("<ul>")
            for symbol, outdir, report in index_entries:
                rel_path = os.path.relpath(os.path.join(outdir, report), root_outdir)
                f.write(f'<li><a href="{rel_path}">{symbol} Report</a></li>')
            f.write("</ul></body></html>")
        print(f"Batch index written to {index_path}")

def _parse_args():
    p = argparse.ArgumentParser(description="Run all strategies and emit consolidated metrics.")
    p.add_argument("csv", nargs="?", help="Input OHLCV CSV (timestamp, open, high, low, close[, volume])")
    p.add_argument("--symbol", default="XAUUSD")
    p.add_argument("--outdir", default="reports")
    p.add_argument("--config", help="YAML config for batch runs")
    return p.parse_args()

def main():
    args = _parse_args()
    if args.config:
        run_from_config(args.config)
    else:
        if not args.csv:
            raise ValueError("CSV file required unless --config is specified.")
        run_all(args.csv, args.symbol, args.outdir)

if __name__ == "__main__":
    main()
