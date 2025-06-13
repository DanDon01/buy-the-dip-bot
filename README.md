# 🤖 Buy The Dip Bot

**Buy The Dip Bot** is your disciplined daily market companion — a Python-powered screener that monitors the S&P 500 and Nasdaq stocks, filters them through your custom checklist, and helps you find prime long- or mid-term investment entry points. It's like a personal scout that never sleeps (except maybe when the market's closed).

## 🚀 Features

- 📉 Scans and scores thousands of stocks daily
- ✅ Uses your custom checklist (e.g., % drop from 52w high, RSI, P/E)
- 🔍 Filters out weak stocks and keeps tracking promising ones for a week
- 📊 Generates a rolling shortlist of top candidates
- 🧠 Detects "Perfect Buy" conditions and logs alerts
- 📁 Outputs daily CSVs + maintains a 7-day memory of watchlist candidates
- 💪 Built using the Kaizen philosophy: continuous daily improvements

## 🛠️ Tech Stack

- Python 3
- `yfinance` for stock data
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
├── output/                 # Daily output CSVs
└── README.md               # You're reading it, legend
```

## 🧾 How It Works

1. **Smart Ticker Selection**
   - Fetches S&P 500 and Nasdaq tickers
   - Filters based on:
     - Market Cap > $100M
     - Average Volume > 100K
     - Major exchanges only (NYSE/Nasdaq)
   - Reduces initial scan from 6000+ to ~800-1000 quality stocks

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
pip install yfinance pandas requests beautifulsoup4
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

- **Optimized Ticker Selection**
  - Reduced scan pool from 6000+ to ~800-1000 stocks
  - Focus on liquid, established companies
  - Better quality opportunities

- **Smart Caching System**
  - 24-hour stock data cache
  - 12-hour scan results cache
  - 80-90% reduction in API calls
  - Automatic cache management

- **Performance Enhancements**
  - Parallel processing of tickers
  - Batch processing to avoid rate limits
  - Real-time progress updates
  - Better error handling

- **Data Quality**
  - Improved validation
  - Better error reporting
  - Consistent data types
  - Reliable caching

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
