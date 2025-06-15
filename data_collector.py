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

                summary = raw_summary if isinstance(raw_summary, dict) else {}
                price_info = raw_price if isinstance(raw_price, dict) else {}

                # Merge into single dict for convenience
                info = {**summary, **price_info}

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
            print(f"\n[Bulk {batch_idx}] Fetching price for {len(batch)} symbols…", flush=True)

            try:
                price_map = Ticker(" ".join(batch), asynchronous=False,
                                   progress=False, timeout=8).price
            except Exception as e:
                print(f"Bulk price request failed ({e}). Retrying after 15 s…", flush=True)
                time.sleep(15)
                try:
                    price_map = Ticker(" ".join(batch), asynchronous=False,
                                       progress=False, timeout=8).price
                except Exception as e:
                    print(f"Bulk price retry failed – skipping this batch. ({e})", flush=True)
                    # Mark all tickers as bad to avoid infinite loops
                    for sym in batch:
                        self._mark_bad(sym)
                    continue

            # iterate batch, build info dict, drop the obvious failures
            survivors = []
            for symbol in batch:
                info = price_map.get(symbol, {}) or {}
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
                print(f"    [{idx}/{len(survivors)}] {symbol} history…", end="", flush=True)
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
    
    def update_daily_scores(self):
        """Update daily scores for filtered tickers."""
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
        
        total = len(stock_data)
        processed = 0
        start_time = time.time()
        
        for ticker, data in stock_data.items():
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
        with open(self.last_update_file, 'r') as f:
            update_data = json.load(f)
        update_data['last_daily_update'] = datetime.now().isoformat()
        with open(self.last_update_file, 'w') as f:
            json.dump(update_data, f)
        
        print("\nDaily scores updated!")
        return scores
    
    def calculate_score(self, data):
        """Calculate score for a single ticker using utils.calculate_score."""
        try:
            df = pd.DataFrame({
                "Close": data["historical_data"]["close"],
                "Volume": data["historical_data"]["volume"],
            })
            return calculate_score(df, data.get("market_cap", 0))
        except Exception as e:
            print(f"Error calculating score: {str(e)}")
            return 0, {}
    
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
        return {
            "ticker": ticker,
            "current_price": price_info["regularMarketPrice"],
            "avg_volume": avg_volume,
            "market_cap": market_cap,
            "exchange": exchange,
            "historical_data": {
                "close": hist_df["Close"].tolist(),
                "volume": hist_df["Volume"].tolist(),
                "high": hist_df["High"].tolist(),
                "low": hist_df["Low"].tolist(),
                "dates": hist_df.index.strftime("%Y-%m-%d").tolist(),
            },
        }

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

if __name__ == "__main__":
    collector = DataCollector()
    collector.update_data() 