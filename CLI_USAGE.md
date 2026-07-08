# 🤖 Buy The Dip Bot - Enhanced CLI Usage Guide

## Overview
The enhanced CLI provides a clear, organized workflow for collecting market data, applying advanced scoring, and exporting results. All outputs are automatically organized into structured directories.

## Quick Start

### 1. Check System Status
```bash
python cli.py --status
```
Shows current data freshness, recommendations, and system state.

### 2. Collect Fresh Data
```bash
# Collect data for top 100 stocks (recommended)
python cli.py --collect-data --top 100

# Or collect for fewer stocks for testing
python cli.py --collect-data --top 50
```

### 3. Apply Enhanced Scoring
```bash
# Score using the filtered stock list
python cli.py --score

# Or score all available stocks
python cli.py --score --all
```

### 4. Export Results
```bash
# Export top 20 results
python cli.py --export --top 20

# Export top 50 results
python cli.py --export --top 50
```

### 4b. Backtesting, Alerts, Portfolio & Market Context (July 2026)
```bash
# Backtesting & ML weight optimization
python cli.py --backtest --top 10 --period 2y --hold 21
python cli.py --optimize-weights [--apply]

# Buy-condition alerts (email/SMS/webhook - see config/env.example)
python cli.py --check-alerts --threshold 75 [--dry-run]

# Portfolio tracking & risk-based position sizing
python cli.py --portfolio
python cli.py --portfolio-add AAPL --shares 10 --price 150
python cli.py --portfolio-sell AAPL --price 170
python cli.py --position-size AAPL

# Market context (feeds the Risk Modifiers scoring layer)
python cli.py --sectors
python cli.py --news --ticker AAPL
python cli.py --options --ticker AAPL
```

### 5. Analyze Specific Stocks
```bash
python cli.py --analyze --ticker AAPL
python cli.py --analyze --ticker MSFT
```

## Complete Workflow Example

```bash
# 1. Check what we have
python cli.py --status

# 2. Collect fresh data for top 100 stocks
python cli.py --collect-data --top 100

# 3. Apply enhanced 4-layer scoring
python cli.py --score

# 4. Export top 20 opportunities
python cli.py --export --top 20

# 5. Analyze specific stocks
python cli.py --analyze --ticker AAPL
```

## File Organization

The CLI automatically organizes all outputs into structured directories:

```
output/
├── filters/        # Filtered ticker lists and universes
├── exports/        # CSV export files with scoring results
├── reports/        # JSON reports with detailed analysis
├── alerts.json     # Stock alerts
├── watchlist.json  # Watchlist data
└── scan_*.csv      # Scan results
```

### Filter Files (`output/filters/`)
- `filtered_universe_N_TIMESTAMP.csv` - Filtered stock universe
- `filtered_top_*.csv` - Legacy filter files (auto-moved)

### Export Files (`output/exports/`)
- `top_N_enhanced_TIMESTAMP.csv` - Full scoring details with layer breakdown
- `top_N_TIMESTAMP.csv` - Simple format with key metrics
- `top_N_scores.csv` - Legacy format for compatibility

### Report Files (`output/reports/`)
- `data_collection_report_TIMESTAMP.json` - Collection statistics
- `scoring_report_TIMESTAMP.json` - Scoring analysis and distribution

## Command Reference

### Main Commands
| Command | Description | Example |
|---------|-------------|---------|
| `--status` | Show system status and recommendations | `python cli.py --status` |
| `--collect-data` | Collect fresh market data | `python cli.py --collect-data --top 100` |
| `--score` | Apply enhanced 4-layer scoring | `python cli.py --score` |
| `--export` | Export results to CSV | `python cli.py --export --top 20` |
| `--analyze` | Detailed stock analysis | `python cli.py --analyze --ticker AAPL` |
| `--cleanup` | Organize scattered files | `python cli.py --cleanup` |

### Parameters
| Parameter | Description | Default | Example |
|-----------|-------------|---------|---------|
| `--top N` | Number of stocks to process | 100 | `--top 50` |
| `--ticker SYMBOL` | Stock ticker for analysis | - | `--ticker AAPL` |
| `--all` | Score all stocks (not just filtered) | False | `--all` |

## Enhanced Features

### 1. Clear Progress Reporting
- Step-by-step workflow indicators
- Time estimates and completion status
- Success/warning/error messages with context

### 2. Automatic File Organization
- All outputs go to organized directories
- Consistent naming with timestamps
- Automatic cleanup of scattered files

### 3. Comprehensive Status Checking
- Data freshness monitoring
- Recommendations for next steps
- Recent activity summary

### 4. Detailed Stock Analysis
- Complete scoring breakdown
- Investment recommendations
- Risk assessment

### 5. Legacy Command Support
- Old commands still work with warnings
- Automatic migration to new workflow
- Backward compatibility maintained

## Scoring Methodology

The enhanced scoring uses a 4-layer approach:

1. **Quality Gate (35%)** - Business quality filter
2. **Dip Signal (45%)** - Optimal dip detection
3. **Reversal Spark (15%)** - Momentum shift signals
4. **Risk Modifiers (±10%)** - Market context adjustments

### Score Interpretation
- **>70**: High quality opportunities
- **40-70**: Medium quality prospects
- **<40**: Low quality (filtered out)

## Troubleshooting

### No Data Found
```bash
# If you see "No stock data found"
python cli.py --collect-data --top 100
```

### Stale Data
```bash
# If data is old (>6 hours)
python cli.py --collect-data --top 100
python cli.py --score
```

### Scattered Files
```bash
# If files are disorganized
python cli.py --cleanup
```

### API Rate Limits
- The system includes automatic rate limiting
- Collection may take several minutes for large datasets
- Progress is shown during long operations

## Migration from Old CLI

### Old vs New Commands
| Old Command | New Command | Notes |
|-------------|-------------|-------|
| `--fetch` | `--collect-data` | More descriptive |
| `--filter` | `--collect-data` | Integrated workflow |
| `--update` | `--collect-data` | Unified data collection |

### Automatic Migration
The CLI automatically detects old commands and provides migration guidance:
```bash
# Old command still works with warning
python cli.py --fetch
# ⚠️ Legacy commands detected. Please use: --collect-data
```

## Best Practices

1. **Start with Status**: Always check `--status` first
2. **Collect Fresh Data**: Use `--collect-data` for new analysis
3. **Regular Scoring**: Re-score every 12 hours for fresh signals
4. **Organized Exports**: Use timestamped exports for tracking
5. **Specific Analysis**: Use `--analyze` for detailed stock research

## Performance Tips

- Use `--top 50` for quick testing
- Use `--top 500` for comprehensive analysis
- Check `--status` to avoid unnecessary data collection
- Use `--cleanup` periodically to maintain organization 