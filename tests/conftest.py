"""Shared test fixtures - synthetic market data, no network access needed."""

import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def make_price_series(n_days=400, start_price=100.0, drift=0.0003,
                      vol=0.02, seed=1, dip_at=None, dip_size=0.30):
    """Generate a synthetic OHLCV DataFrame. Optionally inject a dip."""
    rng = np.random.default_rng(seed)
    returns = rng.normal(drift, vol, n_days)
    if dip_at is not None:
        # Spread a crash over ~10 days ending at dip_at
        crash_per_day = 1 - (1 - dip_size) ** (1 / 10)
        for i in range(max(0, dip_at - 10), dip_at):
            returns[i] = -crash_per_day
    close = start_price * np.cumprod(1 + returns)
    high = close * (1 + rng.uniform(0, 0.01, n_days))
    low = close * (1 - rng.uniform(0, 0.01, n_days))
    volume = rng.integers(500_000, 1_500_000, n_days).astype(float)
    if dip_at is not None:
        volume[max(0, dip_at - 3):dip_at + 1] *= 2.2   # capitulation volume
    dates = pd.bdate_range("2024-01-02", periods=n_days)
    return pd.DataFrame({"Close": close, "High": high, "Low": low,
                         "Open": close, "Volume": volume}, index=dates)


@pytest.fixture
def flat_market():
    return make_price_series(seed=7, drift=0.0, vol=0.005)


@pytest.fixture
def dipped_stock():
    return make_price_series(seed=3, dip_at=300, dip_size=0.30)
