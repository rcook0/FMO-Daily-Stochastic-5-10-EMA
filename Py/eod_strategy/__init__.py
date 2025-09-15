"""
EOD Continuation Strategy package
---------------------------------
Convenience imports for quick access.

Usage:
    from eod_strategy import (
        StrategyConfig, run_strategy_on_dataframe,
        simulate_positions, compare_signals, run_core_strategy
    )
"""

from .eod_continuation import StrategyConfig, run_strategy_on_dataframe
from .simulator import simulate_positions
from .compare_logs import compare_signals
from .core_strategy import run_core_strategy

__all__ = [
    "StrategyConfig",
    "run_strategy_on_dataframe",
    "simulate_positions",
    "compare_signals",
    "run_core_strategy",
]
