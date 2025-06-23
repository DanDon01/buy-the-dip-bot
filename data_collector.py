import pandas as pd
from yahooquery import Ticker
import json
import os
from utils import (
    get_sp500_tickers,
    get_nasdaq_tickers,
    ensure_cache_dir,
    calculate_score,
    load_valid_tickers,
)
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from itertools import islice
from dotenv import load_dotenv

# Load environment variables from .env (if present) early so FINNHUB_API_KEY is available
load_dotenv()

# Integrate Finnhub for fundamental data (bulk API) while retaining Yahoo for refresh
try:
    from collectors.finnhub_collector import FinnhubCollector
except Exception:
    FinnhubCollector = None  # type: ignore – handled at runtime

BULK_PRICE_SIZE = 150   # 1 500 is Yahoo's hard max, 150 keeps responses small
HISTORY_RATE_LIMIT = 1  # seconds between history calls

class DataCollector:
    def __init__(self):
        self.cache_dir = "cache"
        self.data_file = os.path.join(self.cache_dir, "stock_data.json")
        self.tickers_file = os.path.join(self.cache_dir, "filtered_tickers.json")
        self.scores_file = os.path.join(self.cache_dir, "daily_scores.json")
        self.last_update_file = os.path.join(self.cache_dir, "last_update.json")
        self.bad_file = os.path.join(self.cache_dir, "unsupported.json")
        ensure_cache_dir()

        # Optional Finnhub integration (for fundamental *bulk* API calls)
        self._finnhub = None
        if FinnhubCollector is not None:
            try:
                self._finnhub = FinnhubCollector()
                print("📡 Finnhub integration enabled – using it for fundamentals.")
            except Exception as e:
                # Non-fatal – we fall back to yahoo-only if key missing
                print(f"⚠️  Finnhub disabled: {e}")
                self._finnhub = None

        # load previously identified bad tickers
        self.bad_tickers = self._load_bad_tickers()
    
    def needs_weekly_update(self):
        """Check if weekly data needs to be updated."""
        try:
            if not os.path.exists(self.last_update_file):
                return True
            
            with open(self.last_update_file, 'r') as f:
                last_update = datetime.fromisoformat(json.load(f)['last_weekly_update'])
            
            # Update if more than 7 days old
            return datetime.now() - last_update > timedelta(days=7)
        except Exception:
            return True
    
    def needs_daily_update(self):
        """Check if daily scores need to be updated."""
        try:
            if not os.path.exists(self.scores_file):
                return True
            
            with open(self.scores_file, 'r') as f:
                scores_data = json.load(f)
                last_update = datetime.fromisoformat(scores_data['last_update'])
            
            # Update if more than 24 hours old
            return datetime.now() - last_update > timedelta(hours=24)
        except Exception:
            return True
    
    def _clean_ticker(self, ticker):
        """Clean ticker symbol for Yahoo Finance API."""
        # Remove any special characters and convert to uppercase
        cleaned = ''.join(c for c in ticker.upper() if c.isalnum() or c == '.')
        # Handle special cases
        if '^' in ticker:
            # Convert ^ to - for preferred shares
            cleaned = ticker.replace('^', '-')
        return cleaned

    def _fetch_stock_data(self, ticker):
        """Fetch stock data with proper rate limiting and error handling."""
        cleaned_ticker = self._clean_ticker(ticker)
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                # Add delay between attempts
                if attempt > 0:
                    time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                
                # Get basic info with yahooquery
                stock = Ticker(cleaned_ticker)
                # yahooquery sometimes returns a string like "No summary detail found"
                raw_summary = stock.summary_detail.get(cleaned_ticker, {})
                raw_price   = stock.price.get(cleaned_ticker, {})
                # ENHANCED: Fetch additional data sources for comprehensive metrics
                raw_financial = stock.financial_data.get(cleaned_ticker, {})
                raw_stats = stock.key_stats.get(cleaned_ticker, {})
                raw_profile = stock.asset_profile.get(cleaned_ticker, {})

                summary = raw_summary if isinstance(raw_summary, dict) else {}
                price_info = raw_price if isinstance(raw_price, dict) else {}
                financial_info = raw_financial if isinstance(raw_financial, dict) else {}
                stats_info = raw_stats if isinstance(raw_stats, dict) else {}
                profile_info = raw_profile if isinstance(raw_profile, dict) else {}

                # ENHANCED: Merge all data sources for comprehensive information
                info = {
                    **summary,
                    **price_info,
                    **financial_info,
                    **stats_info,
                    **profile_info,
                }

                # Required: price & market cap > 0
                if (
                    "regularMarketPrice" not in info or info["regularMarketPrice"] in (None, 0)
                    or "marketCap" not in info or info["marketCap"] in (None, 0)
                ):
                    print(
                        f"✗ {ticker}: Missing price or marketCap in price module -> unsupported"
                    )
                    self._mark_bad(ticker)
                    return None

                # Volume: accept either intraday volume or 10-day average
                vol = info.get("regularMarketVolume", 0) or info.get("averageDailyVolume10Day", 0)
                if vol in (None, 0):
                    print(f"✗ {ticker}: Missing usable volume figure -> unsupported")
                    self._mark_bad(ticker)
                    return None

                current_price = info["regularMarketPrice"]
                if not current_price or current_price <= 0:
                    print(f"✗ {ticker}: Invalid price data (value={current_price})")
                    self._mark_bad(ticker)
                    return None
                    
                # Get historical data with timeout
                hist = stock.history(period='1mo', interval='1d')
                if hist is None or hist.empty:
                    print(f"✗ {ticker}: No historical data")
                    return None
                if isinstance(hist.index, pd.MultiIndex):
                    hist = hist.xs(cleaned_ticker, level=0, drop_level=True)
                # Convert to UTC then strip timezone to ensure a uniform tz-naive index
                hist.index = pd.to_datetime(hist.index, utc=True).tz_convert(None)
                # Standardise column names (Close/Volume/High/Low)
                hist.rename(columns=lambda c: c.title(), inplace=True)
                
                # Calculate average volume
                avg_volume = hist['Volume'].mean()
                if avg_volume <= 0:
                    # fall back to volume from price info
                    avg_volume = vol
                    
                # Get market cap
                market_cap = info['marketCap']
                if market_cap <= 0:
                    print(f"✗ {ticker}: Invalid market cap (value={market_cap})")
                    self._mark_bad(ticker)
                    return None
                    
                # Get exchange
                exchange = info.get('exchange', info.get('exchangeName', ''))
                if not exchange:
                    print(f"✗ {ticker}: No exchange data in price module")
                    self._mark_bad(ticker)
                    return None
                    
                # Print success with data
                print(f"✓ {ticker}: Price=${current_price:.2f}, Vol={avg_volume:,.0f}, Cap=${market_cap:,.0f}, Ex={exchange}")
                
                # Build compact historical structure expected by calculate_score
                historical_data = {
                    'close': hist['Close'].tolist(),
                    'volume': hist['Volume'].tolist(),
                    'high': hist['High'].tolist(),
                    'low': hist['Low'].tolist(),
                    'dates': hist.index.strftime('%Y-%m-%d').tolist()
                }

                return {
                    'ticker': ticker,
                    'current_price': current_price,
                    'avg_volume': avg_volume,
                    'market_cap': market_cap,
                    'exchange': exchange,
                    'historical_data': historical_data
                }
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"! {ticker}: Attempt {attempt + 1} failed - {str(e)}")
                    continue
                print(f"✗ {ticker}: Failed after {max_retries} attempts - {str(e)}")
                self._mark_bad(ticker)
                return None

    def process_ticker_batch(self, tickers):
        """
        Bulk-fetch price for many symbols in one request, then
        serially download history for the survivors.
        """
        all_stock_data = {}

        for batch_idx, batch in enumerate(self._chunked(tickers, BULK_PRICE_SIZE), 1):
            print(f"\n🌐 [API] [Bulk {batch_idx}] Fetching price for {len(batch)} symbols…", flush=True)

            try:
                bulk_tkr = Ticker(" ".join(batch), asynchronous=False,
                                   progress=False, timeout=8)
                price_map = bulk_tkr.price
                summary_map = bulk_tkr.summary_detail or {}
                stats_map = bulk_tkr.key_stats or {}
                # ENHANCED: Fetch additional data sources for comprehensive metrics
                financial_map = bulk_tkr.financial_data or {}
                profile_map = bulk_tkr.asset_profile or {}
            except Exception as e:
                print(f"Bulk price request failed ({e}). Retrying after 15 s…", flush=True)
                time.sleep(15)
                try:
                    bulk_tkr = Ticker(" ".join(batch), asynchronous=False,
                                       progress=False, timeout=8)
                    price_map = bulk_tkr.price
                    summary_map = bulk_tkr.summary_detail or {}
                    stats_map = bulk_tkr.key_stats or {}
                    # ENHANCED: Retry with additional data sources
                    financial_map = bulk_tkr.financial_data or {}
                    profile_map = bulk_tkr.asset_profile or {}
                except Exception as e:
                    print(f"Bulk price retry failed – skipping this batch. ({e})", flush=True)
                    # Mark all tickers as bad to avoid infinite loops
                    for sym in batch:
                        self._mark_bad(sym)
                    continue

            # iterate batch, build info dict, drop the obvious failures
            survivors = []
            for symbol in batch:
                # Safely handle API responses that might be strings instead of dicts
                summary_data = summary_map.get(symbol, {})
                stats_data = stats_map.get(symbol, {})
                price_data = price_map.get(symbol, {})
                # ENHANCED: Include additional data sources
                financial_data = financial_map.get(symbol, {})
                profile_data = profile_map.get(symbol, {})
                
                # Ensure all data sources are dicts before unpacking
                if not isinstance(summary_data, dict):
                    summary_data = {}
                if not isinstance(stats_data, dict):
                    stats_data = {}
                if not isinstance(price_data, dict):
                    price_data = {}
                if not isinstance(financial_data, dict):
                    financial_data = {}
                if not isinstance(profile_data, dict):
                    profile_data = {}
                
                # ENHANCED: Merge all data sources for comprehensive information
                info = {
                    **summary_data,
                    **stats_data,
                    **price_data,
                    **financial_data,
                    **profile_data,
                }
                ok = (
                    info.get("regularMarketPrice", 0) > 0
                    and info.get("marketCap", 0) > 0
                )
                if ok:
                    survivors.append((symbol, info))
                else:
                    self._mark_bad(symbol)

            # for each survivor fetch history (one call / sec)
            for idx, (symbol, info) in enumerate(survivors, 1):
                p = info.get("regularMarketPrice")
                cap = info.get("marketCap")
                price_str = f"${p:.2f}" if isinstance(p, (int, float)) and p else "n/a"
                cap_str = f"{cap/1e9:.1f}B" if isinstance(cap, (int, float)) and cap else "n/a"
                yr_hi = info.get("fiftyTwoWeekHigh")
                yr_lo = info.get("fiftyTwoWeekLow")
                hi_str = f"${yr_hi:.2f}" if isinstance(yr_hi, (int, float)) and yr_hi else "n/a"
                if p and yr_hi:
                    pct_below = ((yr_hi - p) / yr_hi) * 100
                    drop_str = f"{pct_below:5.1f}%"
                else:
                    drop_str = " n/a "
                
                # ENHANCED: Show additional key metrics in progress display
                fcf = info.get("freeCashflow")
                pe = info.get("trailingPE")
                fcf_str = f"FCF:{fcf/1e6:.0f}M" if isinstance(fcf, (int, float)) and fcf else "FCF:n/a"
                pe_str = f"PE:{pe:.1f}" if isinstance(pe, (int, float)) and pe else "PE:n/a"
                
                print(
                    f"    🌐 [API] [{idx}/{len(survivors)}] {symbol:<6} | Price {price_str:<8} | 52W Hi {hi_str:<8} | Δ {drop_str:<6} | Cap {cap_str:<6} | {fcf_str:<10} | {pe_str:<8} -> history…",
                    end="",
                    flush=True,
                )
                hist = self._fetch_history(symbol)
                if hist is None or hist.empty:
                    # mark missing history so we don't retry endlessly
                    self._mark_bad(symbol)
                    print(" FAIL")
                    time.sleep(HISTORY_RATE_LIMIT)
                    continue
                record = self._assemble_record(symbol, info, hist)
                all_stock_data[symbol] = record
                print(" OK")
                time.sleep(HISTORY_RATE_LIMIT)

            # write partial progress & split by exchange
            if all_stock_data:
                self.save_data(all_stock_data)
                self._save_by_exchange(all_stock_data)

            # polite pause between bulk price calls
            print("Bulk complete – sleeping 10 s to stay under rate-limit…", flush=True)
            time.sleep(10)

        return all_stock_data

    def initial_filter_tickers(self):
        """Initial filtering of tickers with a test batch first."""
        print("Starting initial ticker filtering...")
        
        # Prefer cached validated tickers to save API calls
        all_tickers = load_valid_tickers(max_age_days=1)
        print(f"Loaded {len(all_tickers)} pre-validated tickers for processing")

        # Resume capability – load any stock data that was already collected
        existing_stock_data = {}
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r") as f:
                    existing_stock_data = json.load(f)
                print(f"Found existing data for {len(existing_stock_data)} tickers – will skip them.")
            except Exception:
                print("Warning: could not read existing stock_data.json – will start fresh.")

        processed_set = set(existing_stock_data.keys())
        # skip tickers we know are bad
        remaining_tickers = [t for t in all_tickers if t not in processed_set and t not in self.bad_tickers]

        if not remaining_tickers:
            print("All tickers already processed. Skipping collection.")
            self.save_data(existing_stock_data)
            # Still run filtering to ensure downstream files are up-to-date
            filtered = self.filter_tickers(existing_stock_data)
            self.save_data(existing_stock_data)
            return existing_stock_data

        # Process a small test batch first (only from remaining tickers)
        test_batch_size = 10
        test_sample = remaining_tickers[:test_batch_size]
        if test_sample:
            print(f"\nTesting with first {len(test_sample)} tickers...")
            test_data = self.process_ticker_batch(test_sample)
        else:
            test_data = {}

        remaining_after_test = [t for t in remaining_tickers if t not in test_data]
        stock_data = self.process_ticker_batch(remaining_after_test) if remaining_after_test else {}

        # Merge newly collected data with anything from previous runs
        all_stock_data = {**existing_stock_data, **test_data, **stock_data}
        
        # Filter and save results
        filtered_tickers = self.filter_tickers(all_stock_data)
        self.save_data(all_stock_data)
        
        return all_stock_data
    
    def update_filtered_data(self):
        """Update data for filtered tickers weekly."""
        try:
            # Load filtered tickers
            with open(self.tickers_file, 'r') as f:
                ticker_data = json.load(f)
                filtered_tickers = ticker_data['tickers']
        except FileNotFoundError:
            print("No filtered tickers found. Performing initial filtering...")
            return self.initial_filter_tickers()
        
        print(f"\nUpdating data for {len(filtered_tickers)} filtered tickers...")
        
        # Process filtered tickers in batches
        stock_data = self.process_ticker_batch(filtered_tickers)
        
        # Update last weekly update timestamp
        with open(self.last_update_file, 'w') as f:
            json.dump({
                'last_weekly_update': datetime.now().isoformat(),
                'last_daily_update': datetime.now().isoformat()
            }, f)
        
        return stock_data
    
    def update_daily_scores(self, ticker_subset: list | None = None):
        """Update daily scores.

        If *ticker_subset* is provided, only those tickers are rescored.
        Otherwise the whole ``stock_data.json`` universe is used.
        """
        try:
            # Load current stock data
            with open(self.data_file, 'r') as f:
                stock_data = json.load(f)
        except FileNotFoundError:
            print("No stock data found. Please run weekly update first.")
            return None
        
        print("\nUpdating daily scores...")
        scores = {
            'last_update': datetime.now().isoformat(),
            'scores': {}
        }

        # Determine which tickers to evaluate
        if ticker_subset:
            tickers_to_process = [t for t in ticker_subset if t in stock_data]
        else:
            tickers_to_process = list(stock_data.keys())

        total = len(tickers_to_process)
        processed = 0
        start_time = time.time()
        
        for ticker in tickers_to_process:
            data = stock_data[ticker]
            processed += 1
            
            if processed % 10 == 0:
                elapsed = time.time() - start_time
                per_ticker = elapsed / processed
                remaining = per_ticker * (total - processed)
                print(f"\rProcessed {processed}/{total} tickers "
                      f"({(processed/total*100):.1f}%) | "
                      f"ETA: {int(remaining/60)}m {int(remaining%60)}s", 
                      end="", flush=True)
            
            try:
                score, score_details = self.calculate_score(data)
                scores['scores'][ticker] = {
                    'score': score,
                    'score_details': score_details,
                    'price': data['current_price'],
                    'timestamp': datetime.now().isoformat()
                }
            except Exception as e:
                print(f"\nError calculating score for {ticker}: {str(e)}")
        
        # Save daily scores
        with open(self.scores_file, 'w') as f:
            json.dump(scores, f, indent=4)
        
        # Update last daily update timestamp
        if os.path.exists(self.last_update_file):
            with open(self.last_update_file, 'r') as f:
                update_data = json.load(f)
        else:
            update_data = {
                'last_weekly_update': datetime.now().isoformat(),
                'last_daily_update': datetime.now().isoformat()
            }
        update_data['last_daily_update'] = datetime.now().isoformat()
        with open(self.last_update_file, 'w') as f:
            json.dump(update_data, f, indent=4)
        
        print("\nDaily scores updated!")
        return scores
    
    def calculate_score(self, record):
        """Enhanced scoring using Phase 2 layered scoring engine."""
        try:
            # Build DataFrame from historical data with proper index
            df = pd.DataFrame(
                {
                    "Close": record["historical_data"]["close"],
                    "Volume": record["historical_data"]["volume"],
                    "High": record["historical_data"]["high"],
                    "Low": record["historical_data"]["low"],
                },
                index=pd.to_datetime(record["historical_data"]["dates"])
            )
            
            # Prepare fundamentals dict
            fundamentals = {
                k: record.get(k)
                for k in (
                    "pe",
                    "forward_pe",
                    "peg",
                    "dividend_yield",
                    "beta",
                    "short_percent_float",
                    "insider_hold_percent",
                )
            }

            # Merge in any Finnhub-provided fundamentals
            if record.get("finnhub_fundamentals"):
                fundamentals.update(record["finnhub_fundamentals"])
            
            # Get original legacy score for fallback compatibility
            try:
                legacy_score, legacy_details = calculate_score(df, fundamentals)
            except Exception as legacy_error:
                print(f"Legacy scoring failed for {record.get('ticker', 'UNKNOWN')}: {legacy_error}")
                legacy_score, legacy_details = 0, {}
            
            # Initialize Phase 2 layered scoring engine
            if not hasattr(self, '_composite_scorer'):
                from scoring.composite_scorer import CompositeScorer
                self._composite_scorer = CompositeScorer()
            
            # Calculate comprehensive layered score
            ticker = record.get('ticker', 'UNKNOWN')
            try:
                # Create pre-computed data structure for enhanced scoring
                pre_computed_data = {
                    'fundamentals': fundamentals,
                    'ticker_data': record,  # Pass the full record for access to all fields
                    'current_price': record.get('current_price'),
                    'market_cap': record.get('market_cap'),
                    'avg_volume': record.get('avg_volume'),
                    'year_high': record.get('year_high'),
                    'year_low': record.get('year_low'),
                    'exchange': record.get('exchange')
                }
                
                layered_score, layered_details = self._composite_scorer.calculate_composite_score(
                    df, ticker, pre_computed_data
                )
                
                # Ensure layered_score is a number, not a tuple
                if isinstance(layered_score, tuple):
                    layered_score = layered_score[0] if len(layered_score) > 0 else 0
                    
            except Exception as layered_error:
                print(f"Enhanced scoring failed for {ticker}: {layered_error}")
                # Use legacy score as fallback
                layered_score = legacy_score
                layered_details = {
                    'error': str(layered_error),
                    'fallback': 'legacy_scoring_used',
                    'layer_scores': {'quality_gate': 0, 'dip_signal': 0, 'reversal_spark': 0, 'risk_adjustment': 0},
                    'overall_grade': 'F',
                    'investment_recommendation': {'action': 'AVOID', 'confidence': 'high', 'reason': 'Enhanced scoring error'}
                }
            
            # Create enhanced score details combining both approaches
            enhanced_details = {
                'legacy_score': legacy_score,
                'legacy_details': legacy_details,
                'layered_score': layered_score,
                'layered_details': layered_details,
                'methodology_compliance': layered_details.get('methodology_compliance', {}),
                'investment_recommendation': layered_details.get('investment_recommendation', {}),
                'overall_grade': layered_details.get('overall_grade', 'F'),
                'layer_scores': layered_details.get('layer_scores', {}),
                'enhanced_available': isinstance(layered_details, dict) and 'layer_scores' in layered_details
            }
            
            # Return the layered score as the primary score (it includes all methodology)
            # Keep legacy score for comparison/fallback
            final_score = max(layered_score, 0)
            
            return final_score, enhanced_details
            
        except Exception as e:
            print(f"Error calculating enhanced score for {record.get('ticker', 'UNKNOWN')}: {e}")
            # Fallback to original scoring if enhancement fails
            try:
                df = pd.DataFrame(
                    {
                        "Close": record["historical_data"]["close"],
                        "Volume": record["historical_data"]["volume"],
                        "High": record["historical_data"]["high"],
                        "Low": record["historical_data"]["low"],
                    }
                )
                fundamentals = {
                    k: record.get(k)
                    for k in (
                        "pe",
                        "forward_pe",
                        "peg",
                        "dividend_yield",
                        "beta",
                        "short_percent_float",
                        "insider_hold_percent",
                    )
                }
                legacy_score, legacy_details = calculate_score(df, fundamentals)
                return legacy_score, {
                    'legacy_score': legacy_score,
                    'legacy_details': legacy_details,
                    'layered_score': 0,
                    'error': str(e),
                    'enhanced_available': False
                }
            except Exception:
                return 0, {'error': str(e), 'enhanced_available': False}
    
    def filter_tickers(self, stock_data, 
                      min_market_cap=1e7,     # $10M (reduced from $100M)
                      min_volume=50000,       # 50K (reduced from 100K)
                      exchanges=['NMS', 'NYQ', 'NGM', 'NCM']):  # Added more exchanges
        """Filter tickers based on criteria."""
        print("\nFiltering tickers based on criteria:")
        print(f"✓ Market Cap > ${min_market_cap/1e6:.1f}M")
        print(f"✓ Average Volume > {min_volume:,}")
        print(f"✓ Exchanges: {', '.join(exchanges)}")
        
        filtered_data = {}
        filtered_out = {
            'market_cap': 0,
            'volume': 0,
            'exchange': 0,
            'total': 0
        }
        
        for ticker, data in stock_data.items():
            filtered_out['total'] += 1
            
            # Check market cap
            if data['market_cap'] < min_market_cap:
                filtered_out['market_cap'] += 1
                continue
                
            # Check volume
            if data['avg_volume'] < min_volume:
                filtered_out['volume'] += 1
                continue
                
            # Check exchange
            if data['exchange'] not in exchanges:
                filtered_out['exchange'] += 1
                continue
            
            filtered_data[ticker] = data
        
        print(f"\nFiltering complete:")
        print(f"✓ {len(filtered_data)} tickers passed filters")
        print(f"✗ {filtered_out['total'] - len(filtered_data)} tickers filtered out")
        print("\nFiltered out by criteria:")
        print(f"  Market Cap: {filtered_out['market_cap']}")
        print(f"  Volume: {filtered_out['volume']}")
        print(f"  Exchange: {filtered_out['exchange']}")
        
        if len(filtered_data) == 0:
            print("\nWARNING: No tickers passed the filters!")
            print("Consider adjusting the filtering criteria:")
            print("1. Lower the minimum market cap")
            print("2. Reduce the minimum volume requirement")
            print("3. Add more exchanges to the allowed list")
        
        return filtered_data
    
    def save_filtered_tickers(self, filtered_data):
        """Save filtered tickers list."""
        filtered_tickers = {
            'last_updated': datetime.now().isoformat(),
            'filter_criteria': {
                'min_market_cap': 1e7,
                'min_volume': 50000,
                'exchanges': ['NMS', 'NYQ', 'NGM', 'NCM']
            },
            'tickers': list(filtered_data.keys()),
            'total_tickers': len(filtered_data)
        }
        
        with open(self.tickers_file, 'w') as f:
            json.dump(filtered_tickers, f, indent=4)
        
        # Also save filtered tickers to CSV for easy access
        pd.DataFrame({'ticker': list(filtered_data.keys())}).to_csv('tickers.csv', index=False)
    
    def save_stock_data(self, stock_data):
        """Save collected stock data."""
        with open(self.data_file, 'w') as f:
            json.dump(stock_data, f, indent=4)
    
    # Backwards-compatibility wrapper used earlier in the code
    def save_data(self, stock_data):
        """Alias to save_stock_data (kept for legacy calls)."""
        self.save_stock_data(stock_data)
    
    def update_data(self):
        """Main function to update data based on schedule."""
        # Check if we need weekly update
        if self.needs_weekly_update():
            print("Weekly data update needed...")
            self.update_filtered_data()
        else:
            print("Weekly data is up to date")
        
        # Check if we need daily update
        if self.needs_daily_update():
            print("Daily scores update needed...")
            self.update_daily_scores()
        else:
            print("Daily scores are up to date")

        # Always ensure last_update_file exists so tracker doesn't error
        if not os.path.exists(self.last_update_file):
            with open(self.last_update_file, "w") as f:
                json.dump({
                    "last_weekly_update": datetime.now().isoformat(),
                    "last_daily_update": datetime.now().isoformat(),
                }, f)

    # ---------- bad-ticker helpers ----------
    def _load_bad_tickers(self):
        try:
            if os.path.exists(self.bad_file):
                with open(self.bad_file, "r") as f:
                    return set(json.load(f))
        except Exception:
            pass
        return set()

    def _save_bad_tickers(self):
        try:
            with open(self.bad_file, "w") as f:
                json.dump(sorted(self.bad_tickers), f, indent=2)
        except Exception:
            pass

    def _mark_bad(self, ticker):
        self.bad_tickers.add(ticker)
        self._save_bad_tickers()

    def _chunked(self, iterable, size):
        it = iter(iterable)
        while chunk := list(islice(it, size)):
            yield chunk

    def _fetch_history(self, ticker):
        """Download 1-month daily history, return cleaned DataFrame or None."""
        try:
            hist = Ticker(ticker).history(period="1mo", interval="1d")
            if hist is None or hist.empty:
                return None
            if isinstance(hist.index, pd.MultiIndex):
                hist = hist.xs(ticker, level=0, drop_level=True)
            hist.index = pd.to_datetime(hist.index, utc=True).tz_convert(None)
            hist.rename(columns=lambda c: c.title(), inplace=True)
            return hist
        except Exception:
            return None

    def _assemble_record(self, ticker, price_info, hist_df):
        """Build the dict structure stored in stock_data.json."""
        avg_volume = hist_df["Volume"].mean()
        if avg_volume <= 0:
            avg_volume = price_info.get("regularMarketVolume", 0) or price_info.get(
                "averageDailyVolume10Day", 0
            )
        market_cap = price_info["marketCap"]
        exchange = price_info.get("exchange", price_info.get("exchangeName", ""))
        # 52-week range
        year_high = price_info.get("fiftyTwoWeekHigh")
        year_low = price_info.get("fiftyTwoWeekLow")

        # Keep year_high and year_low as None if not available from yahooquery
        # No more yfinance fallback to maintain API consistency

        # Fundamental extras
        pe = price_info.get("trailingPE") or price_info.get("trailingPe")
        fwd_pe = price_info.get("forwardPE") or price_info.get("forwardPe")
        peg = price_info.get("pegRatio")
        div_yield = price_info.get("dividendYield")
        beta = price_info.get("beta")
        short_float = price_info.get("shortPercentOfFloat")
        insider_pct = price_info.get("heldPercentInsiders") or price_info.get("insiderHoldPercent")

        # ENHANCED: Additional crucial financial metrics for scoring
        # Cash Flow & Financial Strength metrics (crucial for Quality Gate)
        free_cash_flow = price_info.get("freeCashflow")
        operating_cash_flow = price_info.get("operatingCashflow")
        total_cash = price_info.get("totalCash")
        total_debt = price_info.get("totalDebt")
        ebitda = price_info.get("ebitda")
        
        # Profitability metrics (important for Quality Gate)
        gross_margins = price_info.get("grossMargins")
        operating_margins = price_info.get("operatingMargins")
        profit_margins = price_info.get("profitMargins")
        return_on_equity = price_info.get("returnOnEquity")
        return_on_assets = price_info.get("returnOnAssets")
        
        # Growth metrics (Quality Gate scoring)
        revenue_growth = price_info.get("revenueGrowth")
        earnings_growth = price_info.get("earningsGrowth")
        
        # Additional valuation metrics
        price_to_book = price_info.get("priceToBook")
        price_to_sales = price_info.get("priceToSalesTrailing12Months")
        enterprise_value = price_info.get("enterpriseValue")
        
        # Financial ratios for risk assessment
        debt_to_equity = price_info.get("debtToEquity")
        current_ratio = price_info.get("currentRatio")
        quick_ratio = price_info.get("quickRatio")
        
        # Market & trading metrics
        shares_outstanding = price_info.get("sharesOutstanding")
        float_shares = price_info.get("floatShares")
        avg_daily_volume = price_info.get("averageDailyVolume10Day")
        
        # Dividend & payout information
        payout_ratio = price_info.get("payoutRatio")
        dividend_rate = price_info.get("dividendRate")
        ex_dividend_date = price_info.get("exDividendDate")
        
        # Business information (useful for sector analysis)
        sector = price_info.get("sector", "")
        industry = price_info.get("industry", "")
        
        # Calculate derived metrics for immediate use
        current_price = price_info["regularMarketPrice"]
        
        # % below 52-week high (crucial for dip detection)
        pct_below_52w_high = None
        if year_high and current_price:
            pct_below_52w_high = ((year_high - current_price) / year_high) * 100
        
        # Position in 52-week range (0 = at low, 1 = at high)
        range_position = None
        if year_high and year_low and current_price:
            if year_high > year_low:
                range_position = (current_price - year_low) / (year_high - year_low)
        
        # Free Cash Flow yield (if available)
        fcf_yield = None
        if free_cash_flow and market_cap and market_cap > 0:
            fcf_yield = free_cash_flow / market_cap
        
        # Debt to EBITDA ratio (key risk metric)
        debt_to_ebitda = None
        if total_debt and ebitda and ebitda > 0:
            debt_to_ebitda = total_debt / ebitda

        record = {
            "ticker": ticker,
            "current_price": current_price,
            "avg_volume": avg_volume,
            "market_cap": market_cap,
            "exchange": exchange,
            "year_high": year_high,
            "year_low": year_low,
            
            # Existing fundamental metrics
            "pe": pe,
            "forward_pe": fwd_pe,
            "peg": peg,
            "dividend_yield": div_yield,
            "beta": beta,
            "short_percent_float": short_float,
            "insider_hold_percent": insider_pct,
            
            # ENHANCED: Cash Flow & Financial Strength
            "free_cash_flow": free_cash_flow,
            "operating_cash_flow": operating_cash_flow,
            "total_cash": total_cash,
            "total_debt": total_debt,
            "ebitda": ebitda,
            
            # ENHANCED: Profitability metrics
            "gross_margins": gross_margins,
            "operating_margins": operating_margins,
            "profit_margins": profit_margins,
            "return_on_equity": return_on_equity,
            "return_on_assets": return_on_assets,
            
            # ENHANCED: Growth metrics
            "revenue_growth": revenue_growth,
            "earnings_growth": earnings_growth,
            
            # ENHANCED: Additional valuation metrics
            "price_to_book": price_to_book,
            "price_to_sales": price_to_sales,
            "enterprise_value": enterprise_value,
            
            # ENHANCED: Financial ratios
            "debt_to_equity": debt_to_equity,
            "current_ratio": current_ratio,
            "quick_ratio": quick_ratio,
            
            # ENHANCED: Market & trading metrics
            "shares_outstanding": shares_outstanding,
            "float_shares": float_shares,
            "avg_daily_volume": avg_daily_volume,
            
            # ENHANCED: Dividend information
            "payout_ratio": payout_ratio,
            "dividend_rate": dividend_rate,
            "ex_dividend_date": ex_dividend_date,
            
            # ENHANCED: Business classification
            "sector": sector,
            "industry": industry,
            
            # ENHANCED: Calculated derived metrics
            "pct_below_52w_high": pct_below_52w_high,
            "range_position": range_position,
            "fcf_yield": fcf_yield,
            "debt_to_ebitda": debt_to_ebitda,
            
            "historical_data": {
                "close": hist_df["Close"].tolist(),
                "volume": hist_df["Volume"].tolist(),
                "high": hist_df["High"].tolist(),
                "low": hist_df["Low"].tolist(),
                "dates": hist_df.index.strftime("%Y-%m-%d").tolist(),
            },
        }

        # --- Optional Finnhub fundamentals ---------------------------------
        if self._finnhub is not None:
            try:
                fundamentals = self._finnhub.get_stock_snapshot(ticker)
                if fundamentals:
                    record["finnhub_fundamentals"] = fundamentals
                    
                    # Extract additional company profile data from Finnhub
                    if fundamentals.get("company_name"):
                        record["company_name"] = fundamentals["company_name"]
                    if fundamentals.get("country"):
                        record["country"] = fundamentals["country"]
                    if fundamentals.get("phone"):
                        record["phone"] = fundamentals["phone"]
                    if fundamentals.get("website"):
                        record["website"] = fundamentals["website"]
                    if fundamentals.get("logo"):
                        record["logo"] = fundamentals["logo"]
                    if fundamentals.get("ipo_date"):
                        record["ipo_date"] = fundamentals["ipo_date"]
                    if fundamentals.get("finnhub_industry"):
                        record["finnhub_industry"] = fundamentals["finnhub_industry"]
                    if fundamentals.get("currency"):
                        record["currency"] = fundamentals["currency"]
                    # Note: shares_outstanding might conflict with Yahoo data, so prefix it
                    if fundamentals.get("shares_outstanding"):
                        record["finnhub_shares_outstanding"] = fundamentals["shares_outstanding"]
                        
            except Exception as e:
                print(f"⚠️  Finnhub fundamentals fetch failed for {ticker}: {e}")

        return record

    def _save_by_exchange(self, data, out_dir="cache/exchanges"):
        """Save interim stock data split by exchange for easier inspection/resume."""
        os.makedirs(out_dir, exist_ok=True)

        groups = {}
        for t, d in data.items():
            ex = d.get("exchange", "UNK")
            groups.setdefault(ex, {})[t] = d

        for ex, tickers in groups.items():
            path = os.path.join(out_dir, f"{ex}.json")
            with open(path, "w") as f:
                json.dump(tickers, f, indent=4)

    def update_top_scores(self, top_n=100, recalc_scores: bool = False):
        """Re-fetch price & history for the **top_n** highest-scoring tickers.

        This is useful after the daily scan if you want the very latest data
        for your watch-list without touching the full universe.
        """
        # Load current scores
        try:
            with open(self.scores_file, "r") as f:
                scores_data = json.load(f)
        except FileNotFoundError:
            print("No daily scores found. Run update_daily_scores() first.")
            return None

        # Determine top N tickers by score
        top_records = sorted(
            scores_data.get("scores", {}).items(), key=lambda x: x[1]["score"], reverse=True
        )[:top_n]
        tickers = [t for t, _ in top_records]

        # If we don't have enough tickers in scores.json (e.g. first run),
        # fall back to the filtered_top_500 CSV to pad the list.
        if len(tickers) < top_n:
            from run_filter import run_filter

            extra = run_filter(top_n=top_n)
            # Keep order stable & avoid duplicates
            for sym in extra:
                if sym not in tickers and len(tickers) < top_n:
                    tickers.append(sym)

        print(f"Updating detailed data for {len(tickers)} top-scoring tickers…")
        # Process tickers – this will update stock_data.json and caches in place
        self.process_ticker_batch(tickers)

        # After fresh data, optionally recompute their scores so file stays consistent
        if recalc_scores:
            self.update_daily_scores(tickers)

        return tickers

    # ------------------------------------------------------------------
    # Compatibility alias (CLI deep_analyze expects collect_batch)
    # ------------------------------------------------------------------
    def collect_batch(self, tickers):
        """Alias for :py:meth:`process_ticker_batch` kept for backward-compatibility.

        The CLI's Tier-3 deep-analysis step still calls ``collect_batch``.
        To avoid breaking existing workflows we simply forward the call
        here. Any return value from ``process_ticker_batch`` is propagated
        unchanged.
        """
        return self.process_ticker_batch(tickers)

if __name__ == "__main__":
    collector = DataCollector()
    collector.update_data() 