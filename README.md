# 🤖 Buy The Dip Bot

**Buy The Dip Bot** is your disciplined daily market companion — a Python-powered screener that monitors the S&P 500 and Nasdaq stocks, filters them through your custom checklist, and helps you find prime long- or mid-term investment entry points. It's like a personal scout that never sleeps (except maybe when the market's closed).

## 🚀 Features

- 📉 Scans and scores thousands of stocks daily
- ✅ Uses your custom checklist (e.g., % drop from 52w high, RSI, P/E)
- 🔍 Filters out weak stocks and keeps tracking promising ones for a week
- 📊 Generates a rolling shortlist of top candidates
- 🧠 Detects “Perfect Buy” conditions and logs alerts
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
├── alerts_log.csv          # Log of any “Perfect Buy” matches
├── output/                 # Daily output CSVs
└── README.md               # You’re reading it, legend
```

## 🧾 How It Works

1. Scans your chosen tickers (default: top Nasdaq/S&P stocks)
2. Calculates % drop from 52w high, RSI, and P/E ratio
3. Applies scoring model to each stock
4. Tracks strong contenders across multiple days
5. Logs "Perfect Buy" opportunities immediately
6. Promotes top 10 stocks each week to a dedicated shortlist

## ⚙️ To Run It

Install requirements:

```bash
pip install yfinance pandas
```

Then simply run:

```bash
python tracker.py
```

Output CSV will be saved in `output/` and your watchlist will auto-update.

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

Buy The Dip Bot doesn’t predict the market — it just **never misses an opportunity** again.
