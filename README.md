# 🤖 Buy The Dip Bot

**Buy The Dip Bot** is your disciplined daily market companion — a Python-powered screener that monitors the S&P 500 and Nasdaq stocks, filters them through your custom checklist, and helps you find prime long- or mid-term investment entry points. It's like a personal scout that never sleeps (except maybe when the market's closed).

## 🚀 Features

- 📉 Scans and scores thousands of U.S. stocks every day
- ♻️ Seamlessly resumes after interruptions thanks to persistent caches (validated tickers, unsupported symbols, stock data)
- ✅ Enhanced scoring model (52-week dip, RSI bands, volume spike, down-streak, market-cap weight)
- 🔍 Filters out weak stocks and keeps tracking promising ones for a week
- 🗂️ Writes per-exchange JSON snapshots for quick debugging
- 📊 Generates daily CSVs + maintains rolling watch-list & alert log
- 🧠 Detects "Perfect Buy" conditions and logs alerts
- 💪 Built using the Kaizen philosophy: continuous daily improvements

## 🛠️ Tech Stack

- Python 3
- `yahooquery` for stock data (faster & fewer rate-limits)
- `pandas` for data wrangling
- JSON for internal state tracking
- CSV output for easy review

## 📦 Folder Structure

```
📁 buy-the-dip-bot/
├── tracker.py              # Main scanner script
├── utils.py                # RSI, scoring, helper functions
├── tickers.csv             # List of stock tickers to scan
├── daily_watchlist.json    # Rolling 7-day tracked candidates
├── alerts_log.csv          # Log of any "Perfect Buy" matches
├── cache/                  # Cached stock data and scan results
│   └── stock_info_cache.json
│   ├── validated_tickers.json
│   ├── unsupported.json
│   ├── stock_data.json
│   └── daily_scores.json
│   └── stock_info_cache.json
├── output/                 # Daily output CSVs
└── README.md               # You're reading it, legend
```

## 🧾 How It Works

1. **Smart Ticker Selection**
   - Fetches S&P 500 and Nasdaq tickers
   - Filters based on:
     - Market Cap > $10M
     - Average Volume > 50K
     - Major US exchanges (NYSE, Nasdaq, NGM, NCM)
   - Reduces initial scan from 6000+ to ~2 000 quality stocks

2. **Efficient Data Management**
   - Implements smart caching system
   - Caches stock data for 24 hours
   - Stores scan results for 12 hours
   - Reduces API calls by 80-90%
   - Automatically manages cache updates

3. **Scanning Process**
   - Scans filtered tickers in parallel batches
   - Calculates:
     - 5-day RSI
     - Price drops from 5-day high
     - Volume analysis
   - Scores stocks based on multiple criteria
   - Updates progress in real-time

4. **Results Management**
   - Maintains 7-day watchlist
   - Logs "Perfect Buy" opportunities
   - Saves daily scan results
   - Tracks cache performance

## ⚙️ To Run It

Install requirements:

```bash
pip install yahooquery pandas requests beautifulsoup4
```

Then simply run:

```bash
python tracker.py
```

The bot will:
1. Check for recent cached results
2. Use cache if available (within 12 hours)
3. Perform new scan if needed
4. Save results to `output/` directory
5. Update watchlist automatically

## 🔧 Recent Improvements

- **Switched to yahooquery** — avoids the heavy rate-limits of `yfinance` and supports bulk price requests
- **Bulk + Serial Fetch Strategy** — 150-symbol price bulks followed by one-per-second history calls stay safely under Yahoo limits
- **Resume & Robustness** — caches validated tickers, skips unsupported symbols, and restarts exactly where it left off
- **Per-Exchange Snapshots** — interim JSON files split by exchange help quick inspection & debugging
- **Scoring Overhaul** — new metrics (52-week dip, RSI tiers, volume spike, down-streak, market-cap weight) spread scores 0-100
- **Lower Filter Thresholds** — market-cap & volume floors lowered (>$10 M, >50 K) to surface more small-cap opportunities
- **Cleaner Logs** — more explicit reasons when a symbol is rejected and progress bars everywhere

## 💡 Coming Soon

- Earnings date detection
- News sentiment analysis
- Sector-aware diversification controls
- Telegram/email alerts
- Streamlit dashboard view
- Portfolio integration

## 🧙 Author

Created by [Dan] – an engineer, market ninja, and general AI sorcerer.

---

Buy The Dip Bot doesn't predict the market — it just **never misses an opportunity** again.
