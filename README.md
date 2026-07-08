# 🤖 Buy The Dip Bot

**Buy The Dip Bot** is an advanced AI-powered trading dashboard that implements a sophisticated 3-tier hierarchical system for identifying optimal "buy-the-dip" opportunities across thousands of stocks. Built with Python + Flask backend and React TypeScript frontend, it provides real-time scoring, parameter tuning, and investment recommendations.

## 🚀 Key Features

### 🎯 3-Tier Hierarchical System
- **Level 1 Master List**: ~2000 validated stocks from 6969 initial candidates (refreshed monthly)
- **Level 2 Screening Lists**: Top 500/250/100 ranked stocks (refreshed daily/weekly)  
- **Level 3 Deep Analysis**: Full data collection for final picks (real-time)

### 🧠 Advanced 4-Layer Scoring Engine
- **Quality Gate (35%)**: Fundamental analysis & business quality
- **Dip Signal (45%)**: Core dip detection & sweet spot analysis
- **Reversal Spark (15%)**: Momentum shifts & technical indicators
- **Risk Adjustment (±10%)**: Market context & risk modifiers

### 🎮 Interactive Scoring Tuner
- **Real-time parameter adjustment** with 10 strategic presets
- **Live testing** against 234 stocks with fundamental data
- **Enhanced vs basic data** calculations for comprehensive coverage
- **Immediate feedback** on score changes and recommendation impacts

### 📊 Modern Web Dashboard
- **Stock detail pages** with layered radar charts
- **Investment recommendations** with key strengths/risks
- **Performance metrics** and layer breakdowns
- **Action center** for running data collection and scoring

## 🛠️ Tech Stack

### Backend
- **Python 3.11+** with Flask web framework
- **yfinance** (1.x) for Yahoo Finance market data — replaced the unmaintained
  `yahooquery` after Yahoo's cookie/crumb API changes broke it; all access
  goes through the unified `market_data.py` layer with global rate limiting
- **Finnhub API** for fundamentals and company news
- **Pandas / NumPy** for data processing and analysis
- **Advanced caching** system with JSON persistence

### Frontend  
- **React 19** with TypeScript 5.8 and Vite 6
- **Tailwind CSS** for modern styling
- **Recharts 3** for interactive data visualization
- **Responsive design** for all device sizes

### Data Management
- **Smart caching** reduces API calls by 95%
- **Rate limiting** with 0.5s delays to prevent API bans
- **Graceful interruption** handling with Ctrl+C support
- **Persistent state** across application restarts

## 🔑 Setup & Installation

### 1. API Keys
Set your **Finnhub** API key as an environment variable:

```bash
# Windows (PowerShell)
$Env:FINNHUB_API_KEY = "<your-key>"

# macOS / Linux
export FINNHUB_API_KEY="<your-key>"
```

Or create a `.env` file in the project root:
```text
FINNHUB_API_KEY=<your-key>
```

### 2. Backend Setup
```bash
# Install Python dependencies
pip install -r requirements.txt

# Run the Flask backend (port 5001)
python app.py
```

### 3. Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install Node.js dependencies
npm install

# Start development server (port 5173)
npm run dev
```

### 4. Access the Application
- **Frontend Dashboard**: http://localhost:5173
- **Backend API**: http://localhost:5001

## 📁 Project Structure

```
📁 buy-the-dip-bot/
├── 🐍 Backend (Python/Flask)
│   ├── app.py                  # Main Flask application
│   ├── cli.py                  # Command-line interface
│   ├── master_list.py          # Level 1: Master list builder
│   ├── data_collector.py       # Data collection engine
│   ├── utils.py               # Utility functions
│   ├── tracker.py             # Legacy scanner
│   ├── scoring/               # 4-Layer scoring system
│   │   ├── composite_scorer.py
│   │   ├── quality_gate.py
│   │   ├── dip_signal.py
│   │   ├── reversal_spark.py
│   │   └── risk_modifiers.py
│   ├── collectors/            # Data collection modules
│   │   ├── finnhub_collector.py
│   │   ├── fundamental_data.py
│   │   ├── technical_indicators.py
│   │   └── volume_analysis.py
│   └── cache/                 # Data persistence
│       ├── master_list.json   # Level 1 data
│       ├── daily_scores.json  # Scoring results
│       ├── stock_data.json    # Historical data
│       └── screening_lists/   # Level 2 data
├── ⚛️ Frontend (React/TypeScript)
│   ├── src/
│   │   ├── App.tsx            # Main application
│   │   ├── components/        # Reusable components
│   │   │   ├── StockSidebar.tsx
│   │   │   ├── LayeredRadarChart.tsx
│   │   │   ├── PerformanceMetrics.tsx
│   │   │   └── InvestmentRecommendation.tsx
│   │   └── pages/             # Application pages
│   │       ├── HomePage.tsx
│   │       ├── StockDetailPage.tsx
│   │       ├── ScoringTuningPage.tsx
│   │       └── BuyListPage.tsx
│   ├── package.json
│   └── vite.config.ts
├── config/                    # Configuration files
│   └── scoring_parameters.json
├── output/                    # Generated reports
└── 📚 Documentation
    ├── CLI_USAGE.md
    ├── HIERARCHICAL_SYSTEM.md
    └── ENHANCEMENT_PLAN.md
```

## 🎯 How It Works

### 1. **Master List Generation** (Level 1)
```bash
python cli.py --build-master-list
```
- Validates 6969 stock tickers
- Filters by market cap ($100M+) and volume (100K+)
- Creates master list of ~2000 quality stocks
- Refreshed monthly for optimal coverage

### 2. **Screening & Ranking** (Level 2)  
```bash
python cli.py --screen --top 250
```
- Ranks master list by composite scores
- Generates screening lists (Top 500/250/100)
- Refreshed daily/weekly for active monitoring
- Focuses resources on highest-potential stocks

### 3. **Deep Analysis** (Level 3)
```bash
python cli.py --analyze --top 50
```
- Full data collection for final candidates
- Complete 4-layer scoring analysis
- Real-time monitoring and alerts
- Investment-ready recommendations

### 4. **Interactive Parameter Tuning**
- Access the **Scoring Tuner** in the web dashboard
- Choose from 10 strategic presets:
  - 🚀 Growth Stock Dips (AMD-style)
  - 💰 Value & Dividend Dips  
  - 🔄 Turnaround Recovery
  - 📈 Momentum Pullbacks
  - 💥 Market Crash Hunter
  - And 5 more specialized strategies
- Test parameters against 234 real stocks
- See immediate impact on scores and recommendations

## 🧠 Scoring Methodology

### Quality Gate (35% Weight)
- **Cash Flow Health**: Positive FCF and liquidity
- **Profitability**: ROE, margins, earnings quality
- **Debt Management**: Debt/EBITDA ratios
- **Valuation Sanity**: P/E ratio reasonableness
- **Business Quality**: Competitive moats

### Dip Signal (45% Weight)
- **Drop Severity**: % decline from 52-week high
- **Sweet Spot Detection**: Optimal discount range (15-40%)
- **Oversold RSI**: Technical oversold conditions
- **Volume Signature**: Panic selling vs accumulation
- **Support Levels**: Key technical support zones

### Reversal Spark (15% Weight)
- **MACD Signals**: Bullish momentum crossovers
- **Candlestick Patterns**: Reversal formations
- **Volume Reversal**: Buying interest confirmation
- **Momentum Divergence**: Price vs indicator divergence

### Risk Adjustment (±10%)
- **Sector Momentum**: Industry trends
- **Volatility Regime**: Market risk assessment
- **Liquidity Risk**: Trading volume analysis
- **Macro Timing**: Economic cycle positioning

## 🎮 Usage Examples

### Command Line Interface
```bash
# Build master list from scratch
python cli.py --build-master-list

# Screen top 100 stocks  
python cli.py --screen --top 100

# Analyze top 25 with full scoring
python cli.py --analyze --top 25

# Fresh analysis (ignore cache)
python cli.py --fresh --top 50
```

### Backtesting & Weight Optimization
```bash
# Validate the methodology on 2 years of history, 21-day holds
python cli.py --backtest --top 10 --period 2y --hold 21

# Learn better score weights from the backtest trades (ML optimization)
python cli.py --optimize-weights          # review recommendation
python cli.py --optimize-weights --apply  # write into scoring parameters
```
Reports land in `output/backtests/` with win rate, average return, excess
return vs SPY, Sharpe ratio and max drawdown, plus a per-trade CSV.

### Alerts
```bash
# Email/SMS/webhook alerts for stocks hitting buy conditions
python cli.py --check-alerts --threshold 75

# Preview without sending or recording
python cli.py --check-alerts --dry-run
```
Configure channels via environment variables (see `config/env.example`):
SMTP for email, Twilio for SMS, or any Discord/Slack-compatible webhook.
Alerts deduplicate within a 24h cooldown and are logged to `alerts_log.csv`.

### Portfolio & Position Sizing
```bash
python cli.py --portfolio                              # holdings + P&L
python cli.py --portfolio-add AAPL --shares 10 --price 150
python cli.py --portfolio-sell AAPL --price 170        # close (or --shares N)
python cli.py --position-size AAPL                     # risk-based sizing
```
Position sizing risks a fixed % of capital per trade with an ATR-derived
stop, scaled by score conviction and capped per position.

### Market Context
```bash
python cli.py --sectors                  # sector rotation rankings (11 GICS ETFs)
python cli.py --news --ticker AAPL       # news sentiment (Finnhub + lexicon)
python cli.py --options --ticker AAPL    # put/call ratio, IV skew, max pain
```
Sector rotation and news sentiment automatically feed the Risk Modifiers
scoring layer from their local caches — the scoring loop itself never makes
extra API calls.

### Web Dashboard
1. **Home Page**: Overview and quick actions
2. **Stock Details**: Individual stock analysis with radar charts
3. **Scoring Tuner**: Real-time parameter optimization
4. **Buy List**: Filtered recommendations by strategy

## 🔧 Recent Major Improvements

### 🔄 July 2026 Modernization & Feature Release
- **yahooquery → yfinance migration**: the abandoned `yahooquery` dependency
  (broken by Yahoo's auth changes) was replaced with actively-maintained
  `yfinance` 1.x behind a new unified `market_data.py` access layer
- **Backtesting engine** (`backtesting/`): walk-forward, point-in-time scoring
  with no lookahead; win rate, Sharpe, drawdown and SPY-relative metrics
- **ML weight optimization** (`optimization/`): learns dip-score component
  weights from backtest trades (rank IC + top-quartile return objective)
- **Alerts** (`alerts.py`): email (SMTP), SMS (Twilio) and Discord/Slack
  webhook notifications with cooldown-based deduplication
- **Portfolio & position sizing** (`portfolio.py`): cost-basis tracking,
  realized/unrealized P&L, ATR-based risk sizing with conviction scaling
- **Advanced charting**: new `/api/stock/<t>/chart` endpoint + React
  `AdvancedChart` with SMA 20/50/200, Bollinger Bands, RSI and MACD panels
- **Sector rotation** (`analysis/sector_rotation.py`): 11 GICS sector ETFs
  ranked by relative strength vs SPY, feeding the Risk Modifiers layer
- **News sentiment** (`collectors/news_sentiment.py`): Finnhub headlines
  scored with a financial lexicon, feeding the Risk Modifiers layer
- **Options signals** (`collectors/options_data.py`): put/call ratios, ATM IV,
  IV skew and max pain
- **Frontend restored & upgraded**: missing `package.json`/tsconfigs
  recreated; React 19, Vite 6, TypeScript 5.8, Recharts 3, Tailwind 3.4
- **Test suite** (`tests/`): 28 offline unit tests covering the new modules

### 📊 Enhanced Data Coverage
- **234 stocks** now available for testing (vs. 4 previously)
- **Real fundamental scoring** for unscored stocks using P/E, market cap, beta, and price positioning
- **Random sampling** ensures diverse test results across different companies
- **Comprehensive data validation** with enhanced vs basic data indicators
- **Fixed testing issues** where same 4 stocks appeared repeatedly

### 🎯 Scoring System Overhaul
- **4-layer methodology** replaces simple scoring
- **Configurable parameters** with preset strategies
- **Real-time testing** against actual market data
- **Enhanced vs basic data** handling for full coverage

### 🖥️ Modern Web Interface
- **React TypeScript** frontend with responsive design
- **Interactive radar charts** for visual analysis
- **Real-time parameter tuning** with immediate feedback
- **Professional dashboard** with modern UX/UI

### ⚡ Performance & Reliability
- **Rate limiting protection** prevents API bans
- **Graceful error handling** with detailed logging
- **Smart caching** reduces API calls by 95%
- **Resumable operations** with persistent state

### 🔧 Latest Improvements (Dec 2025)
- **Fixed scoring tuner testing** - Now samples from all 234 stocks instead of repeating same 4
- **Enhanced data structure** - Merged scored and unscored stocks for comprehensive testing
- **Real-time fundamental calculations** - Scores unscored stocks using actual P/E, market cap, and technical data
- **Improved frontend display** - Shows data source (Enhanced vs Basic), score changes, and calculation details
- **Better error handling** - Graceful degradation when data is missing with detailed tooltips

## 🚀 Strategic Presets

### Growth & Tech
- **🚀 Growth Stock Dips**: 20-45% drops in high P/E growth stocks
- **💻 Quality Tech Dips**: 25-50% drops in profitable tech companies
- **💳 Blue Chip Pullbacks**: 5-20% dips in established leaders

### Value & Income  
- **💰 Value & Dividend Dips**: 10-30% drops in profitable dividend stocks
- **🍔 Defensive Dividend Dips**: 8-25% dips in dividend aristocrats

### Recovery & Turnaround
- **🔄 Turnaround Recovery**: 40-75% drops with reversal signals
- **🌍 International Deep Value**: 30-70% drops in global stocks

### Market Conditions
- **📈 Momentum Pullbacks**: 8-25% dips in uptrending stocks  
- **📊 Earnings Overreactions**: 15-35% post-earnings drops
- **💥 Market Crash Hunter**: 25-60% drops during corrections

## 🛡️ Risk Management

### API Protection
- **Minimum 0.5s delays** between API calls
- **Rate monitoring** (max 120 calls/min)
- **Timeout limits** (10s max per request)
- **Graceful interruption** with Ctrl+C handling

### Data Quality
- **Comprehensive validation** of all inputs
- **Missing data handling** with graceful degradation
- **Cache integrity** checks and automatic recovery
- **Error logging** with detailed troubleshooting info

## 💡 Roadmap

### Short Term ✅ COMPLETE (July 2026)
- [x] Backtesting engine with historical performance (`--backtest`)
- [x] Email/SMS/webhook alerts for perfect buy conditions (`--check-alerts`)
- [x] Portfolio integration and position sizing (`--portfolio`, `--position-size`)
- [x] Advanced charting with technical overlays (SMA/Bollinger/RSI/MACD)

### Medium Term ✅ COMPLETE (July 2026)
- [x] Machine learning score optimization (`--optimize-weights`)
- [x] News sentiment integration (`--news`, feeds risk modifiers)
- [x] Sector rotation analysis (`--sectors`, feeds risk modifiers)
- [x] Options chain integration (`--options`)

*The former long-term goals (multi-asset support, social trading, mobile app,
institutional API) have been dropped to keep the project focused on doing one
thing well: systematic US-equity dip hunting.*

## 📈 Performance Stats

- **~2000 stocks** in master database
- **234 stocks** with full fundamental data
- **95% API call reduction** through smart caching
- **<0.5s** average response time for web interface
- **4-layer scoring** with 15+ technical indicators
- **10 strategic presets** for different market conditions

## 🧙 Author

Created by **Dan** – an engineer, market analyst, and AI enthusiast passionate about systematic investing and cutting-edge technology.

---

**Buy The Dip Bot** doesn't predict the market — it **systematically identifies and ranks opportunities** so you never miss the next great entry point. 🎯📈
