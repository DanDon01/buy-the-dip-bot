#!/usr/bin/env python3
"""
🤖 Buy The Dip Bot - Enhanced CLI Interface

═══════════════════════════════════════════════════════════════════════════════
📋 QUICK COMMAND REFERENCE
═══════════════════════════════════════════════════════════════════════════════

🏗️  HIERARCHICAL WORKFLOW (RECOMMENDED - SOLVES "TOP N" PROBLEM):
    python cli.py --status                          # Check all system status
    python cli.py --build-master-list              # Build ~2000 quality stocks (monthly)
    python cli.py --screen --top 500               # Screen top 500 from master list
    python cli.py --deep-analyze --top 50          # Deep analysis of top 50

📊 LEGACY WORKFLOW (ORIGINAL - STILL AVAILABLE):
    python cli.py --collect-data --top 100         # Collect data for top 100 stocks
    python cli.py --score                          # Apply enhanced scoring
    python cli.py --export --top 20               # Export top 20 results
    python cli.py --analyze --ticker AAPL         # Analyze specific stock
    python cli.py --cleanup                       # Organize scattered files

🧪 BACKTESTING & OPTIMIZATION:
    python cli.py --backtest --top 10 --period 2y  # Validate methodology historically
    python cli.py --optimize-weights [--apply]     # ML-optimize score weights

🔔 ALERTS & MARKET CONTEXT:
    python cli.py --check-alerts --threshold 75    # Email/SMS/webhook buy alerts
    python cli.py --sectors                        # Sector rotation analysis
    python cli.py --news --ticker AAPL             # News sentiment
    python cli.py --options --ticker AAPL          # Options chain signals

💼 PORTFOLIO:
    python cli.py --portfolio                      # Holdings & P&L
    python cli.py --portfolio-add AAPL --shares 10 --price 150
    python cli.py --portfolio-sell AAPL --price 170
    python cli.py --position-size AAPL             # Risk-based sizing suggestion

🎯 COMMON PARAMETERS:
    --top N         # Number of stocks to process (default: 100)
    --ticker SYMBOL # Specific stock ticker for analysis
    --all           # Process all available stocks (not just top N)
    --fresh         # Use smart filtering from full ticker universe
    --refresh-cache # Refresh ticker universe from live APIs (slow)

💡 FIRST TIME SETUP:
    1. python cli.py --build-master-list           # Takes ~10-15 min, run monthly
    2. python cli.py --screen --top 500            # Fast, run daily/weekly  
    3. python cli.py --deep-analyze --top 50       # Moderate time, as needed

📁 OUTPUT LOCATIONS:
    cache/master_list.json       # Tier 1: Master list (~2000 stocks)
    cache/screening_lists/       # Tier 2: Screening lists (top N)
    output/exports/             # Tier 3: Deep analysis results
    output/filters/             # Legacy: Filtered ticker lists
    output/reports/             # Legacy: Analysis reports

═══════════════════════════════════════════════════════════════════════════════
"""

import argparse
import os
import csv
import glob
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import time

# Import our modules
from tracker import StockTracker
from data_collector import DataCollector
from utils import load_scores, save_top_scores_to_csv, ensure_cache_dir, get_nasdaq_tickers, get_sp500_tickers, filter_tickers, load_valid_tickers, load_cache
from run_filter import run_filter
from master_list import MasterListManager

class BuyTheDipCLI:
    """Enhanced CLI interface with clear workflow and file organization."""
    
    def __init__(self):
        self.output_dir = Path("output")
        self.cache_dir = Path("cache")
        self.reports_dir = self.output_dir / "reports"
        self.exports_dir = self.output_dir / "exports"
        self.filters_dir = self.output_dir / "filters"
        
        # Ensure all directories exist
        for dir_path in [self.output_dir, self.reports_dir, self.exports_dir, self.filters_dir]:
            dir_path.mkdir(exist_ok=True)
        
        # Initialize components
        self.data_collector = DataCollector()
        self.tracker = StockTracker()
        self.master_list_manager = MasterListManager()
        
        # Current timestamp for consistent file naming
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.date_str = datetime.now().strftime("%Y-%m-%d")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 🛠️  UTILITY METHODS
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def print_header(self, title: str):
        """Print a clear section header."""
        print(f"\n{'='*60}")
        print(f"🤖 {title}")
        print(f"{'='*60}")
    
    def print_step(self, step: str, detail: str = ""):
        """Print a workflow step."""
        print(f"\n📋 {step}")
        if detail:
            print(f"   {detail}")
    
    def print_success(self, message: str):
        """Print a success message."""
        print(f"✅ {message}")
    
    def print_warning(self, message: str):
        """Print a warning message."""
        print(f"⚠️  {message}")
    
    def print_error(self, message: str):
        """Print an error message."""
        print(f"❌ {message}")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 📊 STATUS & MONITORING
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def show_status(self):
        """Show current system status and data freshness."""
        self.print_header("SYSTEM STATUS")
        
        # Check cache data
        stock_data_file = self.cache_dir / "stock_data.json"
        scores_file = self.cache_dir / "daily_scores.json"
        
        if stock_data_file.exists():
            mod_time = datetime.fromtimestamp(stock_data_file.stat().st_mtime)
            age_hours = (datetime.now() - mod_time).total_seconds() / 3600
            
            with open(stock_data_file, 'r') as f:
                data = json.load(f)
                stock_count = len(data)
            
            print(f"📊 Stock Data: {stock_count} stocks")
            print(f"🕐 Last Updated: {mod_time.strftime('%Y-%m-%d %H:%M')} ({age_hours:.1f} hours ago)")
            
            if age_hours > 24:
                self.print_warning("Stock data is more than 24 hours old")
            elif age_hours > 6:
                self.print_warning("Stock data is more than 6 hours old")
            else:
                self.print_success("Stock data is fresh")
        else:
            self.print_warning("No stock data found - run --collect-data first")
        
        # Check scores data
        if scores_file.exists():
            mod_time = datetime.fromtimestamp(scores_file.stat().st_mtime)
            age_hours = (datetime.now() - mod_time).total_seconds() / 3600
            
            scores_data = load_scores()
            scores_count = len(scores_data.get('scores', {})) if scores_data else 0
            
            print(f"🎯 Scores: {scores_count} stocks scored")
            print(f"🕐 Last Scored: {mod_time.strftime('%Y-%m-%d %H:%M')} ({age_hours:.1f} hours ago)")
            
            if age_hours > 12:
                self.print_warning("Scores are more than 12 hours old")
            else:
                self.print_success("Scores are recent")
        
        # Show recent exports
        recent_exports = list(self.exports_dir.glob("*"))
        if recent_exports:
            print(f"\n📤 Recent Exports ({len(recent_exports)} files):")
            for export_file in sorted(recent_exports, key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
                mod_time = datetime.fromtimestamp(export_file.stat().st_mtime)
                print(f"   • {export_file.name} ({mod_time.strftime('%Y-%m-%d %H:%M')})")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if not stock_data_file.exists():
            print("   1. Start with: python cli.py --collect-data --top 100")
        elif not scores_file.exists() or age_hours > 12:
            print("   2. Score your data: python cli.py --score")
        else:
            print("   3. Export results: python cli.py --export --top 20")
            print("   4. Analyze specific stocks: python cli.py --analyze --ticker AAPL")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 📊 LEGACY WORKFLOW METHODS (ORIGINAL SYSTEM)
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def collect_data(self, top_n: int = 500, fresh: bool = False, refresh_cache: bool = False):
        """Collect fresh market data for analysis."""
        self.print_header(f"DATA COLLECTION - TOP {top_n} STOCKS")
        
        try:
            if fresh:
                if refresh_cache:
                    # Step 1: Get completely fresh ticker universe
                    self.print_step("Step 1: Refreshing ticker universe from live APIs")
                    print("   🌐 Fetching current NASDAQ listings...")
                    print("   🌐 Fetching current NYSE listings...")
                    print("   🔄 This will take a few minutes but ensures fresh data...")
                    
                    from utils import get_nasdaq_tickers, get_sp500_tickers
                    
                    # Get fresh tickers from multiple sources
                    nasdaq_tickers = get_nasdaq_tickers()
                    sp500_tickers = get_sp500_tickers()
                    
                    # Combine and deduplicate
                    fresh_ticker_universe = list(set(nasdaq_tickers + sp500_tickers))
                    print(f"   ✅ Found {len(fresh_ticker_universe)} fresh tickers")
                    
                    # Quick filter by basic criteria (no API calls needed)
                    self.print_step("Step 2: Basic filtering (no API calls)")
                    
                    # Filter out obvious non-stocks
                    filtered_tickers = []
                    for ticker in fresh_ticker_universe:
                        # Skip ETFs, funds, and obvious non-stocks
                        if any(x in ticker for x in ['.', '-', '^', '=']):
                            continue
                        if len(ticker) > 5:  # Most stocks are 1-5 characters
                            continue
                        filtered_tickers.append(ticker)
                    
                    print(f"   ✅ Filtered to {len(filtered_tickers)} candidate tickers")
                    
                    # Now collect data for a reasonable sample
                    sample_size = min(top_n * 3, 1500)  # 3x requested size, max 1500
                    selected_tickers = filtered_tickers[:sample_size]
                    print(f"   🎯 Collecting data for {len(selected_tickers)} tickers")
                    
                else:
                    # Step 1: Use cached validated tickers with cached market cap filtering
                    self.print_step("Step 1: Smart filtering from cached ticker universe")
                    print("   🗂️  Loading 6,387 validated tickers from cache...")
                    print("   📊 Applying market cap and volume filters using cached data...")
                    
                    # Get validated ticker list (this is fast - just loads JSON)
                    all_tickers = load_valid_tickers(max_age_days=7)  # Allow week-old cache
                    print(f"   ✅ Loaded {len(all_tickers)} validated tickers")
                    
                    # Load cached market cap data 
                    cached_info = load_cache()
                    print(f"   📈 Found cached info for {len(cached_info)} stocks")
                    
                    # Filter using cached data first (very fast)
                    self.print_step("Step 2: Filtering by market cap and volume (cached data)")
                    
                    # Basic filters - much more reasonable than the original
                    MIN_MARKET_CAP = 1e8      # $100M minimum (reasonable threshold)
                    MIN_VOLUME = 100000       # 100K volume minimum
                    EXCHANGES = {'NMS', 'NYQ', 'NGM', 'NCM'}  # Major exchanges
                    
                    print(f"   🎯 Market Cap > ${MIN_MARKET_CAP/1e6:.0f}M")
                    print(f"   🎯 Volume > {MIN_VOLUME:,}")
                    print(f"   🎯 Exchanges: {', '.join(EXCHANGES)}")
                    
                    filtered_candidates = []
                    cache_hits = 0
                    
                    # Build ticker-to-data mapping from hash-keyed cache
                    ticker_cache = {}
                    for cache_key, cache_entry in cached_info.items():
                        if 'data' in cache_entry and 'ticker' in cache_entry['data']:
                            ticker = cache_entry['data']['ticker']
                            ticker_cache[ticker] = cache_entry['data']
                    
                    print(f"   🔍 Built ticker cache mapping for {len(ticker_cache)} stocks")
                    
                    for ticker in all_tickers:
                        if ticker in ticker_cache:
                            cache_hits += 1
                            info = ticker_cache[ticker]
                            
                            # Apply filters using cached data
                            market_cap = info.get('market_cap', 0)
                            avg_volume = info.get('volume', 0)  # Note: it's 'volume' not 'avg_volume'
                            exchange = info.get('exchange', '')
                            
                            if (market_cap >= MIN_MARKET_CAP and 
                                avg_volume >= MIN_VOLUME and 
                                exchange in EXCHANGES):
                                filtered_candidates.append(ticker)
                    
                    print(f"   📊 Cache hit rate: {cache_hits/len(all_tickers)*100:.1f}% ({cache_hits:,}/{len(all_tickers):,})")
                    print(f"   ✅ Found {len(filtered_candidates)} quality candidates")
                    
                    # Select top N candidates
                    selected_tickers = filtered_candidates[:top_n]
                    print(f"   🎯 Selected top {len(selected_tickers)} for data collection")
            
            else:
                # Use existing filter files (backward compatibility)
                self.print_step("Step 1: Loading existing filter files")
                selected_tickers = self._load_filtered_tickers(top_n)
                print(f"   ✅ Loaded {len(selected_tickers)} tickers from existing filters")
            
            if not selected_tickers:
                print("❌ No tickers to process!")
                return
            
            # Step 3: Collect detailed data
            self.print_step(f"Step 3: Collecting detailed data for {len(selected_tickers)} stocks")
            print("   📊 This includes: price data, fundamentals, technical indicators, volume analysis")
            print("   ⏱️  Estimated time: ~2-3 seconds per stock")
            print("   🔄 Progress will be shown every 10 stocks...")
            
            # Initialize data collector
            collector = DataCollector()
            
            # Collect data with progress reporting
            collected_data = collector.process_ticker_batch(selected_tickers)
            success_count = len(collected_data) if collected_data else 0
            
            self.print_success("DATA COLLECTION COMPLETE")
            print(f"   ✅ Successfully collected data for {success_count} stocks")
            print(f"   📁 Data saved to: cache/stock_data.json")
            print(f"   📊 Ready for scoring with: python cli.py --score")
            
        except Exception as e:
            print(f"❌ Error during data collection: {e}")
            import traceback
            traceback.print_exc()
    
    def score_stocks(self, score_all: bool = False, tickers_to_score: Optional[List[str]] = None):
        """Apply enhanced 4-layer scoring methodology."""
        self.print_header("ENHANCED SCORING ENGINE")
        
        # Check if we have data to score
        stock_data_file = self.cache_dir / "stock_data.json"
        if not stock_data_file.exists():
            self.print_error("No stock data found. Run --collect-data first.")
            return
        
        with open(stock_data_file, 'r') as f:
            stock_data = json.load(f)
            stock_count = len(stock_data)
        
        self.print_step(f"Step 1: Loading {stock_count} stocks for scoring")
        
        try:
            # Apply enhanced scoring
            self.print_step("Step 2: Applying 4-layer scoring methodology")
            print("   📊 Quality Gate (35% weight) - Business quality filter")
            print("   📉 Dip Signal (45% weight) - Optimal dip detection") 
            print("   🔄 Reversal Spark (15% weight) - Momentum shift signals")
            print("   ⚖️  Risk Modifiers (±10%) - Market context adjustments")
            
            start_time = time.time()
            
            # Determine scoring universe
            scoring_tickers = []
            if tickers_to_score:
                scoring_tickers = [t for t in tickers_to_score if t in stock_data]
                print(f"   🎯 Scoring a specific list of {len(scoring_tickers)} stocks.")
            elif not score_all:
                filter_files = list(self.filters_dir.glob("filtered_universe_*_*.csv"))
                if filter_files:
                    latest_filter = max(filter_files, key=lambda x: x.stat().st_mtime)
                    with open(latest_filter, 'r') as f:
                        reader = csv.DictReader(f)
                        scoring_tickers = [row['ticker'] for row in reader]
                    print(f"   🎯 Using filter: {latest_filter.name} ({len(scoring_tickers)} stocks)")
                else:
                    scoring_tickers = list(stock_data.keys())
                    print(f"   🎯 No filter found, scoring all {len(scoring_tickers)} stocks")
            else:
                scoring_tickers = list(stock_data.keys())
                print(f"   🎯 Scoring all {len(scoring_tickers)} stocks (--all flag)")
            
            # Update scores
            self.data_collector.update_daily_scores(scoring_tickers)
            
            scoring_time = time.time() - start_time
            
            # Verify scoring results
            scores_data = load_scores()
            if scores_data and 'scores' in scores_data:
                scored_count = len(scores_data['scores'])
                self.print_success(f"Scored {scored_count} stocks in {scoring_time:.1f} seconds")
                
                # Generate scoring report
                scores = scores_data['scores']
                high_quality = sum(1 for s in scores.values() if s.get('score', 0) > 70)
                medium_quality = sum(1 for s in scores.values() if 40 <= s.get('score', 0) <= 70)
                low_quality = sum(1 for s in scores.values() if s.get('score', 0) < 40)
                
                print(f"   📈 Score Distribution:")
                print(f"      • High Quality (>70): {high_quality} stocks")
                print(f"      • Medium Quality (40-70): {medium_quality} stocks")
                print(f"      • Low Quality (<40): {low_quality} stocks")
                
                # Save scoring report
                report_file = self.reports_dir / f"scoring_report_{self.timestamp}.json"
                report = {
                    'timestamp': datetime.now().isoformat(),
                    'stocks_scored': scored_count,
                    'scoring_time_seconds': scoring_time,
                    'score_distribution': {
                        'high_quality': high_quality,
                        'medium_quality': medium_quality,
                        'low_quality': low_quality
                    },
                    'top_10_scores': sorted(
                        [(ticker, data.get('score', 0)) for ticker, data in scores.items()],
                        key=lambda x: x[1], reverse=True
                    )[:10]
                }
                
                with open(report_file, 'w') as f:
                    json.dump(report, f, indent=2)
                
                print(f"   📁 Report saved: {report_file}")
            else:
                self.print_error("Scoring completed but no results found")
                
        except Exception as e:
            self.print_error(f"Scoring failed: {e}")
            raise
    
    def export_results(self, top_n: int = 50):
        """Export results to organized CSV files."""
        self.print_header(f"EXPORT TOP {top_n} RESULTS")
        
        scores_data = load_scores()
        if not scores_data or 'scores' not in scores_data:
            self.print_error("No scores found. Run --score first.")
            return
        
        try:
            # Prepare records for export
            records = [
                {**{'ticker': ticker}, **info}
                for ticker, info in scores_data['scores'].items()
            ]
            
            if not records:
                self.print_warning("No scored records found")
                return
            
            # Sort by score
            records.sort(key=lambda x: x.get('score', 0), reverse=True)
            top_records = records[:top_n]
            
            self.print_step(f"Step 1: Preparing export for top {len(top_records)} stocks")
            
            # Export enhanced format (with all scoring details)
            enhanced_file = self.exports_dir / f"enhanced_top_{top_n}_{self.timestamp}.csv"
            save_top_scores_to_csv(records, top_n)
            
            # Move the generated files to proper location
            generated_files = [
                f"top_{top_n}_enhanced_{datetime.now().strftime('%Y%m%d')}.csv",
                f"top_{top_n}_{datetime.now().strftime('%Y%m%d')}.csv",
                f"top_{top_n}_scores.csv"
            ]
            
            moved_files = []
            for gen_file in generated_files:
                if os.path.exists(gen_file):
                    # Move from root to exports directory
                    dest_file = self.exports_dir / gen_file
                    if os.path.exists(dest_file):
                        os.remove(dest_file)  # Remove existing
                    os.rename(gen_file, dest_file)
                    moved_files.append(dest_file)
            
            # Also move any files from output/ that should be in exports/
            output_files = list(self.output_dir.glob(f"top_{top_n}*.csv"))
            for out_file in output_files:
                dest_file = self.exports_dir / out_file.name
                if out_file != dest_file and out_file.exists():
                    if dest_file.exists():
                        dest_file.unlink()
                    out_file.rename(dest_file)
                    moved_files.append(dest_file)
            
            self.print_success(f"Exported {len(top_records)} stocks to {len(moved_files)} files")
            
            # Show top performers
            print(f"\n🏆 TOP 10 PERFORMERS:")
            for i, record in enumerate(top_records[:10], 1):
                ticker = record.get('ticker', 'N/A')
                score = record.get('score', 0)
                price = record.get('price', 0)
                print(f"   {i:2d}. {ticker:6s} - Score: {score:5.1f} - Price: ${price:7.2f}")
            
            print(f"\n📁 EXPORTED FILES:")
            for file_path in moved_files:
                size_kb = file_path.stat().st_size / 1024
                print(f"   • {file_path.name} ({size_kb:.1f} KB)")
            
        except Exception as e:
            self.print_error(f"Export failed: {e}")
            raise
    
    def analyze_stock(self, ticker: str):
        """Detailed analysis of a specific stock."""
        self.print_header(f"DETAILED ANALYSIS - {ticker.upper()}")
        
        # Load data
        stock_data_file = self.cache_dir / "stock_data.json"
        scores_data = load_scores()
        
        if not stock_data_file.exists():
            self.print_error("No stock data found. Run --collect-data first.")
            return
        
        with open(stock_data_file, 'r') as f:
            stock_data = json.load(f)
        
        ticker = ticker.upper()
        if ticker not in stock_data:
            self.print_error(f"Stock {ticker} not found in dataset")
            available = list(stock_data.keys())[:10]
            print(f"   Available stocks (first 10): {', '.join(available)}")
            return
        
        try:
            stock_info = stock_data[ticker]
            
            # Basic info
            print(f"📊 BASIC INFORMATION:")
            print(f"   Current Price: ${stock_info.get('current_price', 'N/A')}")
            print(f"   Market Cap: ${stock_info.get('market_cap', 0):,.0f}")
            print(f"   Exchange: {stock_info.get('exchange', 'N/A')}")
            print(f"   52W High: ${stock_info.get('year_high', 'N/A')}")
            print(f"   52W Low: ${stock_info.get('year_low', 'N/A')}")
            
            # Scoring details
            if scores_data and ticker in scores_data.get('scores', {}):
                score_info = scores_data['scores'][ticker]
                score = score_info.get('score', 0)
                details = score_info.get('score_details', {})
                
                print(f"\n🎯 SCORING ANALYSIS:")
                print(f"   Overall Score: {score:.1f}/100")
                
                # Layer scores if available
                if 'layered_details' in details and isinstance(details['layered_details'], dict):
                    layer_scores = details['layered_details'].get('layer_scores', {})
                    if layer_scores:
                        weights = details['layered_details'].get('layer_weights', {})
                        print(f"   Layer Breakdown:")
                        print(f"      • Quality Gate: {layer_scores.get('quality_gate', 0):.1f}/{weights.get('quality_gate', 30)}")
                        print(f"      • Dip Signal: {layer_scores.get('dip_signal', 0):.1f}/{weights.get('dip_signal', 40)}")
                        print(f"      • Reversal Spark: {layer_scores.get('reversal_spark', 0):.1f}/{weights.get('reversal_spark', 15)}")
                        print(f"      • Stabilization: {layer_scores.get('stabilization', 0):.1f}/{weights.get('stabilization', 15)}")
                        print(f"      • Risk Adjustment: {layer_scores.get('risk_adjustment', 0):+.1f}")
                
                # Investment recommendation
                if 'investment_recommendation' in details:
                    rec = details['investment_recommendation']
                    if isinstance(rec, dict):
                        action = rec.get('action', 'N/A')
                        confidence = rec.get('confidence', 'N/A')
                        reason = rec.get('reason', 'N/A')
                        
                        print(f"\n💡 INVESTMENT RECOMMENDATION:")
                        print(f"   Action: {action}")
                        print(f"   Confidence: {confidence}")
                        print(f"   Reason: {reason}")
            else:
                self.print_warning(f"No scoring data found for {ticker}. Run --score first.")
            
        except Exception as e:
            self.print_error(f"Analysis failed: {e}")
    
    def cleanup_files(self):
        """Clean up scattered files and organize them properly."""
        self.print_header("FILE ORGANIZATION CLEANUP")
        
        moved_count = 0
        
        # Move filtered files to filters directory
        filter_patterns = ['filtered_*.csv', 'filtered_top_*.csv']
        for pattern in filter_patterns:
            for file_path in Path('.').glob(pattern):
                dest_path = self.filters_dir / file_path.name
                if dest_path.exists():
                    dest_path.unlink()
                file_path.rename(dest_path)
                moved_count += 1
                print(f"   📁 Moved {file_path.name} → filters/")
        
        # Move export files to exports directory
        export_patterns = ['top_*.csv', '*_scores.csv', 'phase2_*.csv']
        for pattern in export_patterns:
            for file_path in Path('.').glob(pattern):
                if 'filtered' not in file_path.name:  # Don't move filtered files again
                    dest_path = self.exports_dir / file_path.name
                    if dest_path.exists():
                        dest_path.unlink()
                    file_path.rename(dest_path)
                    moved_count += 1
                    print(f"   📁 Moved {file_path.name} → exports/")
        
        if moved_count > 0:
            self.print_success(f"Organized {moved_count} files into proper directories")
        else:
            self.print_success("All files are already properly organized")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 🏗️  HIERARCHICAL WORKFLOW METHODS (NEW SYSTEM)
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def build_master_list(self):
        """Build Tier 1: Master list of ~2000 quality stocks."""
        self.print_header("HIERARCHICAL SYSTEM - TIER 1: MASTER LIST")
        
        # Check if master list already exists and is fresh
        stats = self.master_list_manager.get_master_list_stats()
        if stats and stats['fresh']:
            print(f"✅ Master list already exists and is fresh:")
            print(f"   • Size: {stats['total_stocks']:,} stocks")
            print(f"   • Age: {stats['age_days']} days")
            print(f"   • Created: {stats['created']}")
            
            response = input("\n🤔 Rebuild master list anyway? (y/N): ").strip().lower()
            if response != 'y':
                print("   ⏭️  Skipping master list rebuild")
                return
        
        # Build master list
        try:
            result = self.master_list_manager.build_master_list()
            self.print_success(f"Master list built successfully!")
            if result and result.get('stats'):
                print(f"   📊 Final size: {result['stats']['total_in_master_list']:,} stocks")
                print(f"   ⏱️  Processing time: {result['stats']['processing_time_minutes']:.1f} minutes")
            else:
                self.print_warning("Master list build returned no statistics – verify that at least one stock qualified.")
            print(f"   💾 Saved to: cache/master_list.json")
            
        except Exception as e:
            self.print_error(f"Failed to build master list: {e}")
    
    def build_screening_list(self, size: int):
        """Build Tier 2: Screening list of top N candidates from master list."""
        self.print_header(f"HIERARCHICAL SYSTEM - TIER 2: SCREENING LIST (TOP {size})")
        
        # Check if master list exists
        stats = self.master_list_manager.get_master_list_stats()
        if not stats:
            self.print_error("Master list not found. Run --build-master-list first.")
            return []
        
        if not stats['fresh']:
            self.print_warning(f"Master list is {stats['age_days']} days old (recommended: <30 days)")
            response = input("Continue anyway? (y/N): ").strip().lower()
            if response != 'y':
                print("   ⏭️  Cancelled screening list build")
                return []
        
        try:
            tickers = self.master_list_manager.get_screening_list(size)
            if tickers:
                self.print_success(f"Screening list created: {len(tickers)} tickers")
                print(f"   📋 Sample: {', '.join(tickers[:10])}")
                if len(tickers) > 10:
                    print(f"   ... and {len(tickers) - 10} more")
                return tickers
            else:
                self.print_error("Failed to create screening list")
                return []
                
        except Exception as e:
            self.print_error(f"Failed to build screening list: {e}")
            return []
    
    def deep_analyze_top_stocks(self, top_n: int):
        """Tier 3: Deep analysis with full data collection for final picks."""
        self.print_header(f"HIERARCHICAL SYSTEM - TIER 3: DEEP ANALYSIS (TOP {top_n})")
        
        # Get screening list first
        print(f"   📋 Loading screening list for candidate selection...")
        screening_tickers = self.master_list_manager.get_screening_list(top_n * 3)  # Get 3x for filtering
        if not screening_tickers:
            self.print_error("No screening list available. Run --screen first.")
            return
        
        print(f"   ✅ Found screening list with {len(screening_tickers)} candidates")
        
        # Take top N for deep analysis
        analysis_tickers = screening_tickers[:top_n]
        print(f"   🎯 Selected top {len(analysis_tickers)} stocks for deep analysis:")
        
        # Show selected stocks in batches
        batch_size = 10
        for i in range(0, len(analysis_tickers), batch_size):
            batch = analysis_tickers[i:i+batch_size]
            print(f"      {i+1}-{i+len(batch)}: {', '.join(batch)}")
        
        # Collect full data for these stocks
        self.print_step("Step 1: Collecting comprehensive data")
        print(f"   🌐 This will make API calls for detailed fundamental and technical data")
        print(f"   📊 Expected API calls: ~{len(analysis_tickers) * 3} (basic info + fundamentals + history)")
        
        try:
            start_time = time.time()
            self.data_collector.collect_batch(analysis_tickers)
            elapsed = time.time() - start_time
            self.print_success(f"Data collected for {len(analysis_tickers)} stocks in {elapsed:.1f}s")
            print(f"   💾 Data cached for future use")
        except Exception as e:
            self.print_error(f"Data collection failed: {e}")
            return
        
        # Apply enhanced scoring
        self.print_step("Step 2: Applying enhanced 4-layer scoring")
        print(f"   🧮 Computing quality gates, dip signals, reversal sparks, and risk modifiers")
        print(f"   📈 This analyzes fundamental health, technical patterns, and market conditions")
        
        start_time = time.time()
        self.score_stocks(tickers_to_score=analysis_tickers)
        elapsed = time.time() - start_time
        print(f"   ✅ Scoring completed in {elapsed:.1f}s")
        
        # Export detailed results
        self.print_step("Step 3: Exporting detailed analysis")
        print(f"   📝 Creating comprehensive CSV reports with all metrics")
        self.export_results(top_n)
        
        self.print_success(f"Deep analysis completed for top {top_n} stocks!")
        print(f"   📁 Results saved to output/exports/")
        print(f"   💡 Use these results to make informed investment decisions")
    
    def show_hierarchical_status(self):
        """Show status of the hierarchical system."""
        print("\n🏗️  HIERARCHICAL SYSTEM STATUS")
        print("=" * 50)
        
        # Tier 1: Master List
        stats = self.master_list_manager.get_master_list_stats()
        if stats:
            freshness = "✅ Fresh" if stats['fresh'] else "⚠️  Stale"
            print(f"📊 TIER 1 - Master List: {stats['total_stocks']:,} stocks ({freshness})")
            print(f"   • Age: {stats['age_days']} days")
            print(f"   • Created: {stats['created'][:10]}")
        else:
            print("📊 TIER 1 - Master List: ❌ Not built")
            print("   💡 Run: python cli.py --build-master-list")
        
        # Tier 2: Screening Lists
        screening_dir = Path("cache/screening_lists")
        if screening_dir.exists():
            screening_files = list(screening_dir.glob("*.json"))
            if screening_files:
                print(f"\n🎯 TIER 2 - Screening Lists: {len(screening_files)} available")
                for file_path in sorted(screening_files):
                    try:
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                        created = data.get('created', '')[:16].replace('T', ' ')
                        size = data.get('size', 0)
                        print(f"   • Top {size}: {created}")
                    except Exception:
                        continue
            else:
                print(f"\n🎯 TIER 2 - Screening Lists: ❌ None available")
        else:
            print(f"\n🎯 TIER 2 - Screening Lists: ❌ None available")
            print("   💡 Run: python cli.py --screen --top 500")
        
        # Tier 3: Recent Analysis
        if self.exports_dir.exists():
            recent_exports = list(self.exports_dir.glob("*.csv"))
            if recent_exports:
                latest = max(recent_exports, key=lambda x: x.stat().st_mtime)
                mod_time = datetime.fromtimestamp(latest.stat().st_mtime)
                print(f"\n🔬 TIER 3 - Latest Deep Analysis: {latest.name}")
                print(f"   • Created: {mod_time.strftime('%Y-%m-%d %H:%M')}")
            else:
                print(f"\n🔬 TIER 3 - Deep Analysis: ❌ No recent analysis")
        
        print(f"\n💡 RECOMMENDED WORKFLOW:")
        if not stats:
            print("   1. python cli.py --build-master-list")
            print("   2. python cli.py --screen --top 500") 
            print("   3. python cli.py --deep-analyze --top 50")
        elif not stats['fresh']:
            print("   1. Consider rebuilding master list (>30 days old)")
            print("   2. python cli.py --screen --top 500")
            print("   3. python cli.py --deep-analyze --top 50")
        else:
            print("   1. python cli.py --screen --top 500")
            print("   2. python cli.py --deep-analyze --top 50")

    # ═══════════════════════════════════════════════════════════════════════════════
    # 🚀 2026 FEATURE SET: BACKTESTING, ALERTS, PORTFOLIO, SECTORS, NEWS, OPTIONS
    # ═══════════════════════════════════════════════════════════════════════════════

    def _backtest_universe(self, top_n: int) -> List[str]:
        """Pick tickers for the backtest: screening list > cached stock data."""
        try:
            tickers = self.master_list_manager.get_screening_list(top_n)
            if tickers:
                return tickers[:top_n]
        except Exception:
            pass
        stock_data_file = self.cache_dir / "stock_data.json"
        if stock_data_file.exists():
            with open(stock_data_file, 'r') as f:
                return list(json.load(f).keys())[:top_n]
        return []

    def run_backtest(self, top_n: int, period: str, hold_days: int, rebalance_days: int):
        """Run the historical backtest and save a report."""
        from backtesting import BacktestConfig, fetch_and_run, save_report

        self.print_header(f"BACKTEST - {period} HISTORY, {hold_days}-DAY HOLDS")
        tickers = self._backtest_universe(max(top_n, 50))
        if not tickers:
            self.print_error("No ticker universe available. Run --build-master-list or --collect-data first.")
            return

        print(f"   🎯 Universe: {len(tickers)} tickers | period {period} | "
              f"hold {hold_days}d | rebalance every {rebalance_days}d")
        config = BacktestConfig(top_n=min(top_n, 20), hold_days=hold_days,
                                rebalance_days=rebalance_days)
        result = fetch_and_run(tickers, period=period, config=config)

        summary = result.get('summary', {})
        if not summary.get('total_trades'):
            self.print_warning("Backtest produced no trades (not enough history or no qualifying dips).")
            return

        path = save_report(result)
        self.print_success(f"Backtest complete - {summary['total_trades']} trades")
        print(f"   📈 Win rate:        {summary.get('win_rate_pct', 'n/a')}%")
        print(f"   💰 Avg return:      {summary.get('avg_return_pct', 'n/a')}% per trade")
        print(f"   ⚖️  Avg vs SPY:      {summary.get('avg_excess_return_pct', 'n/a')}%")
        print(f"   📊 Sharpe:          {summary.get('sharpe_ratio', 'n/a')}")
        print(f"   📉 Max drawdown:    {summary.get('max_drawdown_pct', 'n/a')}%")
        print(f"   📁 Report: {path}")
        print(f"   💡 Next: python cli.py --optimize-weights")

    def check_alerts(self, threshold: float, dry_run: bool = False):
        """Scan latest scores and send buy-condition alerts."""
        from alerts import AlertManager
        self.print_header(f"ALERTS - THRESHOLD {threshold}")
        AlertManager(threshold=threshold).check_and_send(dry_run=dry_run)

    def show_sectors(self):
        """Refresh and display sector rotation rankings."""
        from analysis.sector_rotation import refresh_sector_rotation
        self.print_header("SECTOR ROTATION ANALYSIS")
        data = refresh_sector_rotation()
        if not data:
            self.print_error("Could not fetch sector ETF data (network/API issue).")
            return
        bench = data['benchmark']
        print(f"   SPY: 1m {bench['return_1m_pct']}% | 3m {bench['return_3m_pct']}% | 6m {bench['return_6m_pct']}%\n")
        print(f"   {'Rank':<5}{'Sector':<26}{'ETF':<6}{'1m RS':>8}{'3m RS':>8}  Phase")
        for s in data['sectors']:
            print(f"   {s['momentum_rank']:<5}{s['sector']:<26}{s['etf']:<6}"
                  f"{s['rel_strength_1m_pct'] if s['rel_strength_1m_pct'] is not None else 'n/a':>8}"
                  f"{s['rel_strength_3m_pct'] if s['rel_strength_3m_pct'] is not None else 'n/a':>8}"
                  f"  {s['phase']}")
        print(f"\n   💾 Cached to cache/sector_rotation.json (feeds risk-modifier scoring)")

    def show_news(self, ticker: str):
        """Fetch and display news sentiment for a ticker."""
        from collectors.news_sentiment import NewsSentimentCollector
        self.print_header(f"NEWS SENTIMENT - {ticker.upper()}")
        summary = NewsSentimentCollector().get_sentiment(ticker)
        print(f"   Sentiment: {summary['label']} ({summary['sentiment_score']:+.3f})")
        print(f"   Articles: {summary['article_count']} "
              f"(+{summary['positive']} / -{summary['negative']} / ={summary['neutral']})")
        for h in summary.get('headlines', [])[:8]:
            print(f"   [{h['sentiment']:+.2f}] {h['headline'][:90]}")

    def show_options(self, ticker: str):
        """Fetch and display options chain signals for a ticker."""
        from collectors.options_data import OptionsDataCollector
        self.print_header(f"OPTIONS SIGNALS - {ticker.upper()}")
        data = OptionsDataCollector().get_options_summary(ticker)
        if not data.get('available'):
            self.print_warning(f"No options data available for {ticker}")
            return
        print(f"   Expiration: {data['expiration']} | Spot: ${data['spot_price']}")
        print(f"   Put/Call volume ratio: {data['put_call_volume_ratio']}")
        print(f"   Put/Call OI ratio:     {data['put_call_oi_ratio']}")
        print(f"   ATM IV (call/put):     {data['atm_call_iv']} / {data['atm_put_iv']}")
        print(f"   IV skew:               {data['iv_skew']}")
        print(f"   Max pain strike:       {data['max_pain_strike']}")
        for name, signal in (data.get('signals') or {}).items():
            print(f"   🔎 {name}: {signal}")

    def optimize_weights(self, apply_to_config: bool):
        """Learn better score weights from the latest backtest."""
        from optimization import optimize_from_backtest
        self.print_header("ML WEIGHT OPTIMIZATION")
        try:
            result = optimize_from_backtest(apply_to_config=apply_to_config)
        except (FileNotFoundError, ValueError) as e:
            self.print_error(str(e))
            return
        report = result['report']
        print(f"   Trades analyzed:  {report['n_trades']}")
        print(f"   IC (optimized):   {report['information_coefficient']}"
              f"  vs equal-weight baseline {report['baseline_ic_equal_weights']}")
        print(f"   Top-quartile avg: {report['top_quartile_avg_return_pct']}%"
              f"  vs all trades {report['all_trades_avg_return_pct']}%")
        print(f"\n   🎯 Optimized component weights:")
        for k, v in result['optimized_weights'].items():
            print(f"      {k:<8} {v:5.1f}")
        print(f"\n   📁 Saved to config/optimized_weights.json"
              + (" and applied to config/scoring_parameters.json" if apply_to_config else
                 "\n   💡 Re-run with --apply to update live scoring parameters"))

    def show_portfolio(self):
        """Display current holdings and P&L."""
        from portfolio import Portfolio
        self.print_header("PORTFOLIO")
        summary = Portfolio().summary()
        if not summary['positions']:
            print("   (no open positions - add one with --portfolio-add TICKER --shares N --price P)")
        else:
            print(f"   {'Ticker':<8}{'Shares':>10}{'Avg Cost':>10}{'Price':>10}{'Value':>12}{'P&L':>10}{'P&L %':>8}")
            for p in summary['positions']:
                price = f"{p['current_price']:.2f}" if p['current_price'] else "n/a"
                pnl = f"{p['unrealized_pnl']:+.2f}" if p['unrealized_pnl'] is not None else "n/a"
                pnl_pct = f"{p['unrealized_pnl_pct']:+.1f}%" if p['unrealized_pnl_pct'] is not None else "n/a"
                print(f"   {p['ticker']:<8}{p['shares']:>10.2f}{p['avg_cost']:>10.2f}"
                      f"{price:>10}{p['market_value']:>12.2f}{pnl:>10}{pnl_pct:>8}")
            print(f"\n   Total value:      ${summary['total_market_value']:,.2f}")
            print(f"   Unrealized P&L:   ${summary['total_unrealized_pnl']:+,.2f}")
        print(f"   Realized P&L:     ${summary['total_realized_pnl']:+,.2f}")

    def portfolio_add(self, ticker: str, shares: float, price: float):
        from portfolio import Portfolio
        pos = Portfolio().add_position(ticker, shares, price)
        self.print_success(f"Bought {shares} {ticker.upper()} @ ${price:.2f} "
                           f"(now {pos['shares']} shares, avg cost ${pos['avg_cost']:.2f})")

    def portfolio_sell(self, ticker: str, shares: Optional[float], price: float):
        from portfolio import Portfolio
        trade = Portfolio().sell_position(ticker, shares, price)
        self.print_success(f"Sold {trade['shares']} {ticker.upper()} @ ${price:.2f} - "
                           f"realized P&L ${trade['realized_pnl']:+.2f} ({trade['realized_pnl_pct']:+.1f}%)")

    def show_position_size(self, ticker: str):
        """Show a risk-based position sizing suggestion."""
        from portfolio import position_size_for_ticker
        self.print_header(f"POSITION SIZING - {ticker.upper()}")
        try:
            s = position_size_for_ticker(ticker)
        except KeyError as e:
            self.print_error(str(e))
            return
        print(f"   Suggested shares:  {s['shares']}")
        print(f"   Position value:    ${s['position_value']:,.2f} "
              f"({s['position_pct_of_capital']}% of capital)")
        print(f"   Stop-loss price:   ${s['stop_price']} "
              f"(risking ${s['risk_budget']:,.2f})")
        print(f"   Conviction:        {s['conviction_multiplier']}x"
              + ("  ⚠️ capped by max position size" if s['capped_by_max_position'] else ""))

    def _load_filtered_tickers(self, top_n: int) -> List[str]:
        """Load tickers from existing filter files for backward compatibility."""
        try:
            all_tickers = run_filter(verbose=False)
            return all_tickers[:top_n]
        except Exception as e:
            print(f"   ⚠️  Error loading existing filters: {e}")
            print("   💡 Try using --fresh flag for smart filtering")
            return []


def main():
    """Main CLI entry point with improved argument handling."""
    parser = argparse.ArgumentParser(
        description="🤖 Buy The Dip Bot - Enhanced CLI Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🏗️  HIERARCHICAL WORKFLOW (NEW - RECOMMENDED):
  python cli.py --status                          # Check all system status
  python cli.py --build-master-list              # Build ~2000 quality stocks (monthly)
  python cli.py --screen --top 500               # Screen top 500 from master list
  python cli.py --deep-analyze --top 50          # Deep analysis of top 50

📊 LEGACY WORKFLOW (ORIGINAL):
  python cli.py --collect-data --top 100         # Collect data for top 100 stocks  
  python cli.py --score                          # Apply enhanced scoring
  python cli.py --export --top 20               # Export top 20 results
  python cli.py --analyze --ticker AAPL         # Analyze specific stock
  python cli.py --cleanup                       # Organize scattered files

💡 WHY HIERARCHICAL?
  • Solves the "top N" problem with meaningful rankings
  • Avoids inefficient API calls (6969 → 2000 → 500 → 50)
  • Master list refreshes monthly, screening lists daily
  • Much faster and more accurate than legacy approach

📁 OUTPUT ORGANIZATION:
  cache/master_list.json       - Tier 1: Master list (~2000 stocks)
  cache/screening_lists/       - Tier 2: Screening lists (top N)
  output/exports/             - Tier 3: Deep analysis results
        """
    )
    
    # Main workflow commands
    parser.add_argument('--status', action='store_true', 
                       help='Show current system status and recommendations')
    parser.add_argument('--collect-data', action='store_true',
                       help='Collect fresh market data for analysis')
    parser.add_argument('--score', action='store_true',
                       help='Apply enhanced 4-layer scoring methodology')
    parser.add_argument('--export', action='store_true',
                       help='Export results to organized CSV files')
    parser.add_argument('--analyze', action='store_true',
                       help='Detailed analysis of specific stock')
    parser.add_argument('--cleanup', action='store_true',
                       help='Organize scattered files into proper directories')
    
    # Hierarchical system commands (NEW!)
    parser.add_argument('--build-master-list', action='store_true',
                       help='Build Tier 1: Master list of ~2000 quality stocks (monthly refresh)')
    parser.add_argument('--screen', action='store_true',
                       help='Build Tier 2: Screening list of top N candidates from master list')
    parser.add_argument('--deep-analyze', action='store_true',
                       help='Tier 3: Deep analysis with full data collection for final picks')
    
    # 2026 feature set
    parser.add_argument('--backtest', action='store_true',
                       help='Run historical backtest of the dip methodology')
    parser.add_argument('--period', type=str, default='2y',
                       help='History period for --backtest (e.g. 1y, 2y, 5y)')
    parser.add_argument('--hold', type=int, default=21,
                       help='Backtest holding period in trading days (default: 21)')
    parser.add_argument('--rebalance', type=int, default=21,
                       help='Backtest rebalance interval in trading days (default: 21)')
    parser.add_argument('--check-alerts', action='store_true',
                       help='Send email/SMS/webhook alerts for buy-condition stocks')
    parser.add_argument('--threshold', type=float, default=75.0,
                       help='Score threshold for --check-alerts (default: 75)')
    parser.add_argument('--dry-run', action='store_true',
                       help='With --check-alerts: print alerts without sending/recording')
    parser.add_argument('--sectors', action='store_true',
                       help='Refresh and show sector rotation analysis')
    parser.add_argument('--news', action='store_true',
                       help='Show news sentiment for --ticker')
    parser.add_argument('--options', action='store_true',
                       help='Show options chain signals for --ticker')
    parser.add_argument('--optimize-weights', action='store_true',
                       help='Learn score weights from the latest backtest (ML optimization)')
    parser.add_argument('--apply', action='store_true',
                       help='With --optimize-weights: write results into scoring parameters')
    parser.add_argument('--portfolio', action='store_true',
                       help='Show portfolio holdings and P&L')
    parser.add_argument('--portfolio-add', type=str, metavar='TICKER',
                       help='Record a buy (requires --shares and --price)')
    parser.add_argument('--portfolio-sell', type=str, metavar='TICKER',
                       help='Record a sell (requires --price; --shares optional = all)')
    parser.add_argument('--shares', type=float,
                       help='Share count for portfolio commands')
    parser.add_argument('--price', type=float,
                       help='Price for portfolio commands')
    parser.add_argument('--position-size', type=str, metavar='TICKER',
                       help='Risk-based position sizing suggestion for a ticker')

    # Parameters
    parser.add_argument('--top', type=int, default=100,
                       help='Number of top stocks to process (default: 100)')
    parser.add_argument('--ticker', type=str,
                       help='Stock ticker for detailed analysis')
    parser.add_argument('--all', action='store_true',
                       help='Score all available stocks (not just filtered list)')
    parser.add_argument('--fresh', action='store_true',
                       help='Use smart filtering from cached ticker universe (6,387 validated tickers)')
    parser.add_argument('--refresh-cache', action='store_true',
                       help='Refresh the ticker universe by fetching from live APIs (takes a few minutes)')
    
    # Legacy support (deprecated)
    parser.add_argument('--fetch', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--update', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--filter', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--debug', action='store_true', help=argparse.SUPPRESS)
    
    args = parser.parse_args()
    
    # Initialize CLI
    cli = BuyTheDipCLI()
    
    try:
        # Handle legacy commands with warnings
        if args.fetch or args.update or args.filter:
            cli.print_warning("Legacy commands detected. Please use the new workflow:")
            cli.print_warning("--fetch/--update/--filter → --collect-data")
            if args.fetch or args.update:
                args.collect_data = True
        
        # Check if hierarchical commands are used
        hierarchical_commands = [args.build_master_list, args.screen, args.deep_analyze]
        legacy_commands = [args.collect_data, args.score, args.export, args.analyze, args.cleanup]
        feature_commands = [args.backtest, args.check_alerts, args.sectors, args.news,
                            args.options, args.optimize_weights, args.portfolio,
                            bool(args.portfolio_add), bool(args.portfolio_sell),
                            bool(args.position_size)]

        # Execute commands in logical order
        if args.status or (not any(hierarchical_commands + legacy_commands + feature_commands)):
            # Show both legacy and hierarchical status
            cli.show_status()
            cli.show_hierarchical_status()
        
        # Hierarchical system commands (NEW WORKFLOW)
        if args.build_master_list:
            cli.build_master_list()
        
        if args.screen:
            cli.build_screening_list(args.top)
        
        if args.deep_analyze:
            cli.deep_analyze_top_stocks(args.top)
        
        # Legacy workflow commands (ORIGINAL WORKFLOW)
        if args.cleanup:
            cli.cleanup_files()
        
        if args.collect_data:
            cli.collect_data(args.top, args.fresh, args.refresh_cache)
        
        if args.score:
            cli.score_stocks(args.all)
        
        if args.export:
            cli.export_results(args.top)
        
        if args.analyze:
            if not args.ticker:
                cli.print_error("--analyze requires --ticker parameter")
                parser.print_help()
            else:
                cli.analyze_stock(args.ticker)

        # 2026 feature commands
        if args.backtest:
            cli.run_backtest(args.top, args.period, args.hold, args.rebalance)

        if args.optimize_weights:
            cli.optimize_weights(args.apply)

        if args.check_alerts:
            cli.check_alerts(args.threshold, args.dry_run)

        if args.sectors:
            cli.show_sectors()

        if args.news:
            if not args.ticker:
                cli.print_error("--news requires --ticker parameter")
            else:
                cli.show_news(args.ticker)

        if args.options:
            if not args.ticker:
                cli.print_error("--options requires --ticker parameter")
            else:
                cli.show_options(args.ticker)

        if args.portfolio_add:
            if args.shares is None or args.price is None:
                cli.print_error("--portfolio-add requires --shares and --price")
            else:
                cli.portfolio_add(args.portfolio_add, args.shares, args.price)

        if args.portfolio_sell:
            if args.price is None:
                cli.print_error("--portfolio-sell requires --price")
            else:
                cli.portfolio_sell(args.portfolio_sell, args.shares, args.price)

        if args.portfolio:
            cli.show_portfolio()

        if args.position_size:
            cli.show_position_size(args.position_size)
        
        print(f"\n🎉 CLI operations completed successfully!")
        print(f"📁 Check the output/ directory for organized results")
        
    except Exception as e:
        print(f"\n❌ CLI operation failed: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
