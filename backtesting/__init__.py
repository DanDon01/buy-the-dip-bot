"""Backtesting framework for the buy-the-dip methodology (Phase 4)."""

from .engine import (
    BacktestConfig,
    technical_dip_score,
    run_backtest,
    fetch_and_run,
    save_report,
    DEFAULT_WEIGHTS,
)

__all__ = [
    "BacktestConfig",
    "technical_dip_score",
    "run_backtest",
    "fetch_and_run",
    "save_report",
    "DEFAULT_WEIGHTS",
]
