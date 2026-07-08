"""Weight optimizer tests (offline, synthetic trades)."""

import numpy as np

from optimization import WeightOptimizer
from optimization.weight_optimizer import _spearman


def test_spearman_perfect_and_inverse():
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    assert _spearman(x, x) == 1.0
    assert _spearman(x, -x) == -1.0


def test_optimizer_finds_predictive_component():
    """If only one component predicts returns, it should get most weight."""
    rng = np.random.default_rng(0)
    n = 200
    X = rng.uniform(0, 1, size=(n, 5))
    y = X[:, 0] * 0.10 + rng.normal(0, 0.01, n)   # component 0 drives returns

    weights, report = WeightOptimizer(X, y, seed=1).optimize(iterations=800)
    keys = list(weights)
    assert weights[keys[0]] == max(weights.values())
    assert weights[keys[0]] > 40   # dominant share of 100
    assert report["information_coefficient"] > report["baseline_ic_equal_weights"] - 1e-9
    assert abs(sum(weights.values()) - 100) < 1.0


def test_optimizer_report_fields():
    rng = np.random.default_rng(2)
    X = rng.uniform(0, 1, size=(50, 5))
    y = rng.normal(0, 0.05, 50)
    _, report = WeightOptimizer(X, y, seed=2).optimize(iterations=200)
    for field in ("n_trades", "objective", "information_coefficient",
                  "top_quartile_avg_return_pct", "all_trades_avg_return_pct"):
        assert field in report
    assert report["n_trades"] == 50
