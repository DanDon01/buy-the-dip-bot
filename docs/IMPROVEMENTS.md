# Repo Review & Suggested Improvements

*Written July 2026, after the modernization + 5-layer scoring work. Items are
ordered by expected value. Things already fixed during the review are listed
at the bottom.*

---

## High priority

### 1. Replace JSON caches with SQLite
`cache/stock_data.json` holds every stock record (including full price
history) in one file that is rewritten wholesale on every batch. At ~2000
stocks this means multi-MB rewrites per ticker batch, no partial reads, no
indexing, and corruption risk on interrupt.

**Suggestion:** a single `cache/btd.sqlite` with tables `stocks`,
`daily_scores`, `price_history`, `sentiment`, `options`. `sqlite3` is in the
standard library; the change can be isolated behind a small `storage.py`
repository class so callers keep their current shape. Price history could
alternatively live in parquet files per ticker (pandas reads them natively).

### 2. Split `app.py` into Flask blueprints
`app.py` is ~950 lines mixing data loading, JSON cleaning, scoring
simulation, and 20+ routes. Suggested layout:

```
api/
├── __init__.py        # create_app() factory
├── stocks.py          # /api/stocks, /api/stock/*
├── scoring.py         # /api/scoring/*
├── portfolio.py       # /api/portfolio*
├── market.py          # /api/sectors, /api/backtests
└── serialization.py   # clean_data_for_json (single home)
```

`clean_data_for_json`/`_to_native_py_type` currently exist in **both**
`app.py` and `utils.py` with slightly different behaviour — consolidate to
one implementation.

### 3. Delete or quarantine legacy/dead modules
These are unused, undocumented, or broken and confuse every future change:

| File | Status |
|---|---|
| `dashboard.py`, `advanced_dashboard.py` | Streamlit dashboards; `streamlit`/`st_aggrid` aren't even in requirements. Superseded by the React app. |
| `tracker.py` | Legacy scanner; contains literal placeholder bodies (`pass`, `...`). Only `StockTracker()` is instantiated by the CLI and never meaningfully used. |
| `API-test.py`, `debug_api.py`, `quick_test_masterlist.py`, `export_top_50.py` | One-off debug scripts. |
| `run_filter.py` | Only reachable through legacy CLI paths. |

Suggestion: move to a `legacy/` folder (or delete — git history keeps them).

### 4. Backtest the actual 5-layer scorer, not just its technical proxy
The backtester scores with a technical-only approximation because historical
fundamentals aren't available from free sources. Options to close the gap:
- Snapshot `stock_data.json` fundamentals daily (cheap since collection
  already runs) and grow a real point-in-time fundamentals archive over time.
- Or pull historical fundamentals from an API that provides them (FMP,
  Tiingo, EODHD) as an optional integration.
Then the ML optimizer could tune *all five* layer weights against realized
returns instead of only the technical components.

## Medium priority

### 5. CI extras
CI now runs pytest + the frontend build (`.github/workflows/ci.yml`). Worth
adding when convenient: `ruff` (lint+format) for Python, `npm run lint` for
the frontend, and a scheduled weekly run to catch yfinance/API breakage
early.

### 6. Sector-relative Quality Gate thresholds
Quality Gate applies absolute thresholds (P/E < 20 good, margins > 15%
good) across all sectors, which structurally favours some industries (tech
margins vs. retail; bank debt ratios are meaningless). The data already
includes `sector`; store per-sector median P/E / margins in the master list
build and score relative to them.

### 7. Frontend bundle splitting
The build is ~830 kB minified (recharts dominates). Add lazy `import()` for
routes and a `manualChunks: { recharts: ['recharts'] }` in `vite.config.ts`.

### 8. API tests
The pytest suite covers the analytics modules but not the Flask routes. Add
`tests/test_api.py` using `app.test_client()` with a small fixture cache
directory (monkeypatched paths) to lock down response shapes the frontend
depends on.

### 9. Scheduled automation
The pieces exist (collect → score → alert) but nothing runs them on a
schedule. A simple `scheduler.py` (APScheduler) or documented cron/GitHub
Actions examples would complete the loop:
`--screen` daily → `--deep-analyze` daily → `--check-alerts` hourly →
`--sectors` daily → `--backtest`/`--optimize-weights` monthly.

## Lower priority / nice-to-have

- **Typed models:** stock records are free-form dicts everywhere; a
  `dataclass`/`TypedDict` layer (or pydantic) would catch field-name drift
  (`pe` vs `pe_ratio` vs `trailingPE` appear in different modules).
- **Logging:** replace `print()` with the `logging` module (levels,
  timestamps, quiet mode for cron runs).
- **master_list.py duplication:** it reimplements ticker fetching/filtering
  that also lives in `utils.py`; consolidate into one ticker-universe module.
- **Watchlist unification:** the Buy List lives in browser `localStorage`
  while `daily_watchlist.json` lives server-side; give the buy list a small
  backend endpoint so it survives browser changes.
- **Options-informed scoring:** put/call and IV skew are collected but only
  displayed; a small ±2 risk-modifier contribution from options sentiment
  (like news sentiment) would integrate them.
- **Realized-trade feedback loop:** portfolio close-outs record P&L; feed
  those outcomes back into the optimizer's training set alongside backtest
  trades.

---

## Fixed during this review (July 2026)

- Added the **Stabilization layer** (falling-knife filter) and made all layer
  weights configurable via `config/scoring_parameters.json` (see README).
- Removed dead `simulate_new_scoring()` from `app.py` (superseded, uncalled).
- `app.run(debug=...)` now gated behind `FLASK_DEBUG=1` instead of always-on.
- Untracked runtime artifacts (`alerts_log.csv`, `daily_watchlist.json`).
- Added GitHub Actions CI (backend pytest + frontend type-check/build).
- Centralized frontend API access in `src/lib/api.ts` with `VITE_API_URL`
  support (no more hardcoded `localhost:5001` in components).
- New Portfolio and Market Context dashboard pages.
