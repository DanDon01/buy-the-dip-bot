"""
Machine-learning score optimization.

Learns better component weights for the dip score from backtest results.
Every backtest trade records its raw component values (0..1) plus the
realized forward return, so re-weighting is a pure numeric problem - no
re-downloading of market data.

Method: random search over the weight simplex followed by coordinate-ascent
refinement (a deliberately dependency-light optimizer - robust on small,
noisy samples where a gradient fit would overfit). The objective blends:

* Spearman rank correlation between score and forward return (information
  coefficient), and
* mean return of the top-quartile-scored trades (what we'd actually buy).

Usage:
    python cli.py --backtest ...          # produces output/backtests/*.json
    python cli.py --optimize-weights      # learns weights from latest run
    python cli.py --optimize-weights --apply   # also saves to config/

The optimized weights feed the backtester's technical dip score and are
written to config/optimized_weights.json for review; --apply merges them
into config/scoring_parameters.json used by the live scoring tuner.
"""

from __future__ import annotations

import glob
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np

COMPONENT_KEYS = ["drop", "rsi", "volume", "sma", "macd"]
OUT_FILE = os.path.join("config", "optimized_weights.json")


def _spearman(x: np.ndarray, y: np.ndarray) -> float:
    """Spearman rank correlation without a scipy dependency."""
    if len(x) < 3:
        return 0.0
    rx = np.argsort(np.argsort(x)).astype(float)
    ry = np.argsort(np.argsort(y)).astype(float)
    rx -= rx.mean()
    ry -= ry.mean()
    denom = np.sqrt((rx ** 2).sum() * (ry ** 2).sum())
    if denom == 0:
        return 0.0
    return float((rx * ry).sum() / denom)


class WeightOptimizer:
    """Optimizes dip-score component weights against realized returns."""

    def __init__(self, components: np.ndarray, returns: np.ndarray,
                 keys: Optional[List[str]] = None, seed: int = 42):
        """
        Args:
            components: (n_trades, n_components) matrix of raw 0..1 values.
            returns: (n_trades,) realized forward returns (fractions).
            keys: component names, defaults to COMPONENT_KEYS.
        """
        self.X = np.asarray(components, dtype=float)
        self.y = np.asarray(returns, dtype=float)
        self.keys = keys or list(COMPONENT_KEYS)
        self.rng = np.random.default_rng(seed)

    # ------------------------------------------------------------------
    def objective(self, weights: np.ndarray) -> float:
        """Blended objective: rank IC + top-quartile mean return (scaled)."""
        scores = self.X @ weights
        ic = _spearman(scores, self.y)
        k = max(3, len(self.y) // 4)
        top_idx = np.argsort(scores)[-k:]
        top_mean = float(self.y[top_idx].mean())
        overall_mean = float(self.y.mean())
        # Excess of the picked basket over the average opportunity set,
        # scaled so one percentage point ≈ 0.1 objective units.
        edge = (top_mean - overall_mean) * 10
        return 0.6 * ic + 0.4 * edge

    def optimize(self, iterations: int = 3000,
                 refine_rounds: int = 3) -> Tuple[Dict[str, float], Dict]:
        """Run random search + coordinate ascent. Returns (weights, report)."""
        n = self.X.shape[1]

        best_w = np.full(n, 1.0 / n)
        best_obj = self.objective(best_w)

        # --- Phase 1: random search on the simplex ---
        for _ in range(iterations):
            w = self.rng.dirichlet(np.ones(n))
            obj = self.objective(w)
            if obj > best_obj:
                best_obj, best_w = obj, w

        # --- Phase 2: coordinate ascent around the incumbent ---
        step = 0.05
        for _ in range(refine_rounds):
            improved = True
            while improved:
                improved = False
                for i in range(n):
                    for delta in (step, -step):
                        w = best_w.copy()
                        w[i] = max(0.0, w[i] + delta)
                        if w.sum() == 0:
                            continue
                        w = w / w.sum()
                        obj = self.objective(w)
                        if obj > best_obj + 1e-9:
                            best_obj, best_w = obj, w
                            improved = True
            step /= 2

        weights_100 = {k: round(float(w) * 100, 2)
                       for k, w in zip(self.keys, best_w)}
        report = self._report(best_w, best_obj)
        return weights_100, report

    def _report(self, weights: np.ndarray, obj: float) -> Dict:
        scores = self.X @ weights
        k = max(3, len(self.y) // 4)
        top_idx = np.argsort(scores)[-k:]
        equal_w = np.full(len(weights), 1.0 / len(weights))
        return {
            "n_trades": int(len(self.y)),
            "objective": round(obj, 4),
            "information_coefficient": round(_spearman(scores, self.y), 4),
            "baseline_ic_equal_weights": round(_spearman(self.X @ equal_w, self.y), 4),
            "top_quartile_avg_return_pct": round(float(self.y[top_idx].mean()) * 100, 3),
            "all_trades_avg_return_pct": round(float(self.y.mean()) * 100, 3),
        }


# ----------------------------------------------------------------------
# Glue: learn from saved backtest reports
# ----------------------------------------------------------------------
def load_trades_from_backtest(path: Optional[str] = None) -> Tuple[np.ndarray, np.ndarray]:
    """Load (components, returns) matrices from a backtest JSON report."""
    if path is None:
        candidates = sorted(glob.glob(os.path.join("output", "backtests", "backtest_*.json")))
        if not candidates:
            raise FileNotFoundError(
                "No backtest reports found - run `python cli.py --backtest` first.")
        path = candidates[-1]

    with open(path) as f:
        result = json.load(f)

    rows, rets = [], []
    for trade in result.get("trades", []):
        comps = trade.get("components", {})
        if not comps or trade.get("return_pct") is None:
            continue
        rows.append([float(comps.get(k, 0.0)) for k in COMPONENT_KEYS])
        rets.append(float(trade["return_pct"]) / 100)

    if len(rows) < 20:
        raise ValueError(
            f"Only {len(rows)} usable trades in {path} - need at least 20 "
            "for meaningful optimization. Run a longer/wider backtest.")
    return np.array(rows), np.array(rets)


def optimize_from_backtest(path: Optional[str] = None,
                           iterations: int = 3000,
                           apply_to_config: bool = False) -> Dict:
    """End-to-end: load latest backtest, optimize, persist recommendation."""
    X, y = load_trades_from_backtest(path)
    optimizer = WeightOptimizer(X, y)
    weights, report = optimizer.optimize(iterations=iterations)

    output = {
        "optimized_weights": weights,
        "component_keys": COMPONENT_KEYS,
        "report": report,
        "source_backtest": path or "latest",
        "generated": datetime.now().isoformat(),
    }

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    if apply_to_config:
        _apply_to_scoring_parameters(weights)
        output["applied_to_config"] = True

    return output


def _apply_to_scoring_parameters(weights: Dict[str, float]):
    """Map optimized technical components onto the live tuner parameters.

    drop+rsi+volume drive the Dip Signal weight; macd the Reversal Spark;
    sma folds into dip. Quality Gate weight is left untouched (fundamentals
    are not part of the technical backtest).
    """
    params_file = os.path.join("config", "scoring_parameters.json")
    try:
        with open(params_file) as f:
            config = json.load(f)
        params = config.get("parameters", {})
    except (FileNotFoundError, json.JSONDecodeError):
        config, params = {}, {}

    technical_total = sum(weights.values())
    if technical_total <= 0:
        return
    dip_frac = (weights.get("drop", 0) + weights.get("rsi", 0)
                + weights.get("volume", 0) + weights.get("sma", 0)) / technical_total
    rev_frac = weights.get("macd", 0) / technical_total

    quality_weight = params.get("quality_gate_weight", 35)
    remaining = 100 - quality_weight
    params["dip_signal_weight"] = round(remaining * dip_frac, 1)
    params["reversal_spark_weight"] = round(remaining * rev_frac, 1)
    params["quality_gate_weight"] = quality_weight

    config["parameters"] = params
    config["last_updated"] = datetime.now().isoformat()
    config["updated_by"] = "weight_optimizer"
    os.makedirs(os.path.dirname(params_file), exist_ok=True)
    with open(params_file, "w") as f:
        json.dump(config, f, indent=2)
