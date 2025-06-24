import pandas as pd
import numpy as np
from yahooquery import Ticker
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import json
import csv
from io import StringIO
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import contextlib
import os
import sys
import hashlib

# Configure logging to completely silence yfinance
class SilentLogger(logging.Logger):
    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=1):
        pass

# Replace yfinance logger with our silent version
logging.setLoggerClass(SilentLogger)
yf_logger = logging.getLogger('yfinance')
yf_logger.setLevel(logging.CRITICAL)  # Only show critical errors
yf_logger.propagate = False  # Don't propagate to root logger

# Also silence urllib3 (used by yfinance)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').propagate = False

# Cache configuration
CACHE_DIR = "cache"
STOCK_INFO_CACHE = os.path.join(CACHE_DIR, "stock_info_cache.json")
CACHE_EXPIRY = timedelta(days=1)  # Cache expires after 1 day

VALIDATED_FILE = os.path.join(CACHE_DIR, "validated_tickers.json")

def ensure_cache_dir():
    """Ensure cache directory exists."""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

def get_cache_key(ticker, data_type):
    """Generate a cache key for a ticker and data type."""
    return hashlib.md5(f"{ticker}_{data_type}".encode()).hexdigest()

def load_cache():
    """Load the cache from disk."""
    ensure_cache_dir()
    try:
        if os.path.exists(STOCK_INFO_CACHE):
            with open(STOCK_INFO_CACHE, 'r') as f:
                cache = json.load(f)
                # Convert string timestamps back to datetime
                for key, data in cache.items():
                    if 'timestamp' in data:
                        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
                return cache
    except Exception:
        pass
    return {}

def save_cache(cache):
    """Save the cache to disk."""
    ensure_cache_dir()
    try:
        # Convert datetime to string for JSON serialization
        cache_copy = {}
        for key, data in cache.items():
            cache_copy[key] = data.copy()
            if 'timestamp' in data:
                cache_copy[key]['timestamp'] = data['timestamp'].isoformat()
        
        with open(STOCK_INFO_CACHE, 'w') as f:
            json.dump(cache_copy, f, indent=4)
    except Exception as e:
        print(f"Warning: Could not save cache: {str(e)}")

# Initialize cache
_stock_info_cache = load_cache()

@contextlib.contextmanager
def suppress_output():
    """Context manager to suppress stdout and stderr."""
    with open(os.devnull, 'w') as devnull:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = devnull
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            
def load_scores(path="cache/daily_scores.json"):
    with open(path) as f:
        return json.load(f)

def save_top_scores_to_csv(scores, top_n):
    """Write the *top_n* highest-scoring tickers to *output/top_{n}.csv* with enhanced scoring data."""
    if not scores:
        print("No score records supplied – CSV not written.")
        return

    sorted_scores = sorted(scores, key=lambda x: x["score"], reverse=True)[:top_n]

    # Make sure the output directory exists
    os.makedirs("output", exist_ok=True)

    from datetime import datetime
    date_str = datetime.now().strftime("%Y%m%d")
    
    # Enhanced CSV with layer breakdown
    enhanced_path = f"output/top_{top_n}_enhanced_{date_str}.csv"
    enhanced_fieldnames = [
        'ticker', 'score', 'price', 'overall_grade', 'investment_action', 'confidence',
        'quality_gate_score', 'dip_signal_score', 'reversal_spark_score', 'risk_adjustment',
        'quality_grade', 'dip_grade', 'reversal_strength', 'dip_classification',
        'methodology_compliance', 'pe', 'market_cap', 'avg_volume', 'drop_from_high_pct',
        'rsi_14', 'enhanced_available', 'timestamp'
    ]
    
    # Prepare enhanced data
    enhanced_records = []
    for record in sorted_scores:
        enhanced_record = {
            'ticker': record.get('ticker', ''),
            'score': record.get('score', 0),
            'price': record.get('price', 0),
            'timestamp': record.get('timestamp', ''),
            'pe': 'N/A',
            'market_cap': 'N/A',
            'avg_volume': 'N/A',
            'drop_from_high_pct': 'N/A',
            'rsi_14': 'N/A',
            'enhanced_available': False
        }
        
        # Extract enhanced scoring data if available
        score_details = record.get('score_details', {})
        if isinstance(score_details, dict):
            # Check if enhanced scoring is available
            enhanced_available = score_details.get('enhanced_available', False)
            enhanced_record['enhanced_available'] = enhanced_available
            
            if enhanced_available:
                # Extract layer scores
                layer_scores = score_details.get('layer_scores', {})
                enhanced_record.update({
                    'quality_gate_score': layer_scores.get('quality_gate', 0),
                    'dip_signal_score': layer_scores.get('dip_signal', 0),
                    'reversal_spark_score': layer_scores.get('reversal_spark', 0),
                    'risk_adjustment': layer_scores.get('risk_adjustment', 0),
                    'overall_grade': score_details.get('overall_grade', 'F')
                })
                
                # Extract investment recommendation
                investment_rec = score_details.get('investment_recommendation', {})
                enhanced_record.update({
                    'investment_action': investment_rec.get('action', 'AVOID'),
                    'confidence': investment_rec.get('confidence', 'unknown')
                })
                
                # Extract methodology compliance
                methodology = score_details.get('methodology_compliance', {})
                enhanced_record.update({
                    'methodology_compliance': methodology.get('methodology_grade', 'F'),
                    'dip_classification': methodology.get('dip_classification', 'no_dip')
                })
                
                # Extract layer details if available
                layer_details = score_details.get('layered_details', {})
                if isinstance(layer_details, dict):
                    # Quality gate details
                    quality_details = layer_details.get('layer_details', {}).get('quality_gate', {})
                    enhanced_record['quality_grade'] = quality_details.get('quality_grade', 'F')
                    
                    # Dip signal details  
                    dip_details = layer_details.get('layer_details', {}).get('dip_signal', {})
                    enhanced_record['dip_grade'] = dip_details.get('dip_grade', 'F')
                    
                    # Reversal spark details
                    reversal_details = layer_details.get('layer_details', {}).get('reversal_spark', {})
                    enhanced_record['reversal_strength'] = reversal_details.get('reversal_strength', 'minimal')
                    
            else:
                # Fall back to legacy scoring details
                legacy_details = score_details.get('legacy_details', {})
                enhanced_record.update({
                    'quality_gate_score': 0,
                    'dip_signal_score': 0,
                    'reversal_spark_score': 0,
                    'risk_adjustment': 0,
                    'overall_grade': 'F',
                    'investment_action': 'AVOID',
                    'confidence': 'low',
                    'methodology_compliance': 'F',
                    'dip_classification': 'legacy_scoring'
                })
                
                # Extract what we can from legacy scoring
                if 'rsi5' in legacy_details:
                    enhanced_record['rsi_14'] = legacy_details['rsi5']
                if 'pe' in legacy_details:
                    enhanced_record['pe'] = legacy_details['pe']
        
        enhanced_records.append(enhanced_record)
    
    # Write enhanced CSV
    with open(enhanced_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=enhanced_fieldnames)
        writer.writeheader()
        writer.writerows(enhanced_records)
    print(f"✅ Saved {len(enhanced_records)} enhanced records to {enhanced_path}")
    
    # Also create simple CSV for backward compatibility
    simple_path = f"output/top_{top_n}_{date_str}.csv"
    simple_fieldnames = ['ticker', 'score', 'price', 'overall_grade', 'investment_action']
    simple_records = [
        {
            'ticker': record.get('ticker', ''),
            'score': record.get('score', 0),
            'price': record.get('price', 0),
            'overall_grade': record.get('overall_grade', 'F'),
            'investment_action': record.get('investment_action', 'AVOID')
        }
        for record in enhanced_records
    ]
    
    with open(simple_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=simple_fieldnames)
        writer.writeheader()
        writer.writerows(simple_records)
    print(f"✅ Saved {len(simple_records)} simple records to {simple_path}")

    # Legacy CSV (original format)
    legacy_path = f"output/top_{top_n}_scores.csv"
    with open(legacy_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=sorted_scores[0].keys())
        writer.writeheader()
        writer.writerows(sorted_scores)
    print(f"✅ Saved {len(sorted_scores)} legacy records to {legacy_path}")

def calculate_rsi(prices, period=14):
    """Calculate Relative Strength Index (RSI) for a series of prices."""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_stock_data(ticker, period="1wk"):
    """Fetch stock data using yfinance with caching."""
    cache_key = get_cache_key(f"{ticker}_{period}", 'data')
    current_time = datetime.now()
    
    # Check cache first
    if cache_key in _stock_info_cache:
        cached_data = _stock_info_cache[cache_key]
        if current_time - cached_data['timestamp'] < CACHE_EXPIRY:
            # Convert cached data back to DataFrame
            return pd.DataFrame(cached_data['data'])
    
    # If not in cache or expired, fetch from API
    try:
        stock = Ticker(ticker)
        hist = stock.history(period=period, interval='1d')
        if hist is None or hist.empty:
            return None
        # yahooquery returns a MultiIndex (symbol, date). Drop the symbol level for single ticker
        if isinstance(hist.index, pd.MultiIndex):
            hist = hist.xs(ticker, level=0, drop_level=True)
        # Standardise column capitalisation so downstream code stays unchanged (Close / Volume)
        hist.rename(columns=lambda c: c.title(), inplace=True)
        # Ensure required columns exist
        hist = hist[['Close', 'Volume']]
        
        # Update cache
        _stock_info_cache[cache_key] = {
            'timestamp': current_time,
            'data': hist.to_dict('records')
        }
        
        # Save cache periodically
        if len(_stock_info_cache) % 100 == 0:
            save_cache(_stock_info_cache)
        
        return hist
    except Exception:
        return None

def calculate_score(stock_data: pd.DataFrame, fundamentals: dict):
    """Extensive dip-score using technical + fundamental factors."""

    if stock_data is None or len(stock_data) < 20:
        return 0, {}

    try:
        current_price = stock_data["Close"].iloc[-1]
        high_5d = stock_data["Close"].tail(5).max()
        drop_pct = ((high_5d - current_price) / high_5d) * 100

        # RSI 5
        rsi5 = calculate_rsi(stock_data["Close"], period=5).iloc[-1]

        # Volume spike
        vol_avg20 = stock_data["Volume"].tail(20).mean()
        vol_ratio = stock_data["Volume"].iloc[-1] / vol_avg20 * 100

        # SMA200 (if we have ≥200 observations)
        sma200 = stock_data["Close"].rolling(window=200).mean().iloc[-1] if len(stock_data) >= 200 else None
        below_sma = sma200 and current_price < sma200

        # MACD bullish cross last 5 days
        ema12 = stock_data["Close"].ewm(span=12, adjust=False).mean()
        ema26 = stock_data["Close"].ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        bullish = (macd.iloc[-2] < signal.iloc[-2]) and (macd.iloc[-1] > signal.iloc[-1])

        # ATR %
        tr = stock_data[["High", "Low", "Close"]].copy()
        tr["prev_close"] = tr["Close"].shift(1)
        tr["tr"] = tr[["High", "prev_close"]].max(axis=1) - tr[["Low", "prev_close"]].min(axis=1)
        atr14 = tr["tr"].rolling(14).mean().iloc[-1]
        atr_pct = atr14 / current_price * 100 if atr14 else 0

        # Fundamental fields
        pe = fundamentals.get("pe") or fundamentals.get("trailingPE")
        div_yield = fundamentals.get("dividend_yield", 0) or 0
        beta = fundamentals.get("beta", 1)
        short_pct = fundamentals.get("short_percent_float", 0) or 0

        score = 0
        details = {}

        # Price drop – scaled: 1 pt per % drop (above 3 %), capped 30
        pd_pts = 0
        if drop_pct >= 3:
            pd_pts = min(30, int(drop_pct))
        score += pd_pts; details["price_drop"] = pd_pts

        # RSI
        rsi_pts = 25 if rsi5 <= 30 else (10 if rsi5 <= 40 else 0)
        score += rsi_pts; details["rsi5"] = rsi_pts

        # Volume spike
        if vol_ratio >= 200:
            vol_pts = 20
        elif vol_ratio >= 150:
            vol_pts = 15
        elif vol_ratio >= 120:
            vol_pts = 8
        else:
            vol_pts = 0
        score += vol_pts; details["volume_spike"] = vol_pts

        # Trend filters
        sma_pts = 10 if below_sma else 0
        sma50 = stock_data["Close"].rolling(window=50).mean().iloc[-1] if len(stock_data) >= 50 else None
        below_sma50 = sma50 and current_price < sma50
        sma50_pts = 5 if below_sma50 else 0
        score += sma_pts + sma50_pts
        details["below_sma200"] = sma_pts
        details["below_sma50"] = sma50_pts

        # MACD bullish (positive histogram)
        macd_hist = macd.iloc[-1] - signal.iloc[-1]
        macd_pts = 5 if macd_hist > 0 else 0
        score += macd_pts; details["macd_bull_cross"] = macd_pts

        # Valuation – PE
        if pe and pe < 15:
            pe_pts = 10
        elif pe and pe < 25:
            pe_pts = 5
        else:
            pe_pts = 0
        score += pe_pts; details["pe"] = pe_pts

        # Dividend yield bonus
        div_pts = 5 if div_yield and div_yield > 0.03 else 0
        score += div_pts; details["div_yield"] = div_pts

        # Beta penalty for high volatility
        beta_pts = -5 if beta and beta > 2 else 0
        score += beta_pts; details["beta"] = beta_pts

        # Short interest penalty
        short_pts = -10 if short_pct and short_pct > 0.15 else 0
        score += short_pts; details["short_float"] = short_pts

        return max(score, 0), details
    except Exception as e:
        print("Error calculating score:", e)
        return 0, {}

def save_to_json(data, filename):
    """Save data to a JSON file."""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

def load_from_json(filename):
    """Load data from a JSON file."""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def get_sp500_tickers():
    """Fetch S&P 500 tickers from Wikipedia."""
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', {'class': 'wikitable'})
        # Fix the read_html warning by using StringIO
        df = pd.read_html(StringIO(str(table)))[0]
        # Clean ticker symbols (remove dots and special characters)
        tickers = df['Symbol'].str.replace(r'[^A-Z]', '', regex=True).tolist()
        return [t for t in tickers if t]  # Remove empty strings
    except Exception as e:
        print(f"Error fetching S&P 500 tickers: {str(e)}")
        return []

def get_nasdaq_tickers():
    """Fetch Nasdaq tickers from nasdaq.com."""
    try:
        # First try to get the most active stocks
        url = "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=1000&offset=0&download=true"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        data = response.json()
        
        if 'data' in data and 'rows' in data['data']:
            # Clean ticker symbols
            tickers = [row['symbol'].replace('.', '') for row in data['data']['rows']]
            return [t for t in tickers if t]  # Remove empty strings
        return []
    except Exception as e:
        print(f"Error fetching Nasdaq tickers: {str(e)}")
        return []

def validate_ticker(ticker):
    """Validate if a ticker is active and has data."""
    try:
        stock = Ticker(ticker)
        # Only fetch 1 day of data for validation
        hist = stock.history(period='1d', interval='1d')
        if hist is None or hist.empty:
            return False
        if isinstance(hist.index, pd.MultiIndex):
            hist = hist.xs(ticker, level=0, drop_level=True)
        hist.rename(columns=lambda c: c.title(), inplace=True)
        return len(hist[['Close']]) > 0
    except Exception:
        return False

def validate_ticker_batch(tickers, batch_size=100):
    """Validate a batch of tickers efficiently."""
    valid_tickers = []
    invalid_count = 0
    total_batches = (len(tickers) + batch_size - 1) // batch_size
    
    # Process in batches to avoid overwhelming the API
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        current_batch = (i // batch_size) + 1
        print(f"\rValidating batch {current_batch}/{total_batches} "
              f"({len(valid_tickers)} valid, {invalid_count} invalid)", end="", flush=True)
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_ticker = {
                executor.submit(validate_ticker, ticker): ticker 
                for ticker in batch
            }
            
            for future in as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                try:
                    if future.result():
                        valid_tickers.append(ticker)
                    else:
                        invalid_count += 1
                except Exception:
                    invalid_count += 1
        
        # Add delay between batches to avoid rate limiting
        time.sleep(1)
    
    print()  # New line after progress
    return valid_tickers, invalid_count

def get_stock_info(ticker):
    """Get basic stock info for filtering with caching."""
    cache_key = get_cache_key(ticker, 'info')
    current_time = datetime.now()
    
    # Check cache first
    if cache_key in _stock_info_cache:
        cached_data = _stock_info_cache[cache_key]
        if current_time - cached_data['timestamp'] < CACHE_EXPIRY:
            data = cached_data['data'].copy()
            data['_from_cache'] = True
            data['_cache_age_hours'] = (current_time - cached_data['timestamp']).total_seconds() / 3600
            return data
    
    # If not in cache or expired, fetch from API
    try:
        with suppress_output():
            stock = Ticker(ticker)
            # yahooquery exposes multiple info dicts, merge the essentials
            summary = stock.summary_detail.get(ticker, {})
            price   = stock.price.get(ticker, {})
            info    = {**summary, **price}

            data = {
                'ticker': ticker,
                'market_cap': info.get('marketCap', 0),
                'volume': info.get('averageVolume', info.get('averageDailyVolume10Day', 0)),
                'exchange': info.get('exchange', info.get('exchangeName', '')),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                '_from_cache': False,
                '_api_call_time': current_time.isoformat()
            }
            
            # Update cache
            _stock_info_cache[cache_key] = {
                'timestamp': current_time,
                'data': data
            }
            
            # Save cache periodically (every 100 updates)
            if len(_stock_info_cache) % 100 == 0:
                save_cache(_stock_info_cache)
            
            return data
    except Exception as e:
        # Return None but log the error for debugging
        return None

def filter_tickers(tickers, min_market_cap=1e8,  # $100M
                   min_volume=100000,            # 100K average volume
                   exchanges=['NMS', 'NYQ']):    # Nasdaq and NYSE
    """Filter tickers based on key attributes with caching."""
    print("\nFiltering tickers based on criteria:")
    print(f"✓ Market Cap > ${min_market_cap/1e6:.1f}M")
    print(f"✓ Average Volume > {min_volume:,}")
    print(f"✓ Exchanges: {', '.join(exchanges)}")
    
    filtered_tickers = []
    total = len(tickers)
    cached_count = 0
    api_count = 0
    
    print(f"\nAnalyzing {total} tickers...")
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_ticker = {
            executor.submit(get_stock_info, ticker): ticker 
            for ticker in tickers
        }
        
        for i, future in enumerate(as_completed(future_to_ticker), 1):
            if i % 100 == 0:
                print(f"\rProcessed {i}/{total} tickers (Cached: {cached_count}, API: {api_count})", end="", flush=True)
            
            try:
                info = future.result()
                if info:
                    if info.get('_from_cache', False):
                        cached_count += 1
                    else:
                        api_count += 1
                        
                    if all([
                        info['market_cap'] >= min_market_cap,
                        info['volume'] >= min_volume,
                        info['exchange'] in exchanges
                    ]):
                        filtered_tickers.append(info)
            except Exception:
                continue
    
    # Save final cache state
    save_cache(_stock_info_cache)
    
    print(f"\n\nFiltering complete:")
    print(f"✓ {len(filtered_tickers)} tickers passed filters")
    print(f"✗ {total - len(filtered_tickers)} tickers filtered out")
    print(f"📊 Cache hits: {cached_count}, API calls: {api_count}")
    
    # Sort by market cap
    filtered_tickers.sort(key=lambda x: x['market_cap'], reverse=True)
    
    # Save filtered tickers to JSON with metadata
    tickers_data = {
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'filter_criteria': {
            'min_market_cap': min_market_cap,
            'min_volume': min_volume,
            'exchanges': exchanges
        },
        'total_analyzed': total,
        'total_filtered': len(filtered_tickers),
        'cache_stats': {
            'hits': cached_count,
            'api_calls': api_count
        },
        'tickers': filtered_tickers
    }
    
    with open('tickers.json', 'w') as f:
        json.dump(tickers_data, f, indent=4)
    
    # Also update CSV with just the ticker symbols
    pd.DataFrame({'ticker': [t['ticker'] for t in filtered_tickers]}).to_csv('tickers.csv', index=False)
    
    return [t['ticker'] for t in filtered_tickers]

def update_tickers_file():
    """Update tickers.json with filtered tickers."""
    print("Fetching S&P 500 tickers...")
    sp500_tickers = get_sp500_tickers()
    print(f"Found {len(sp500_tickers)} S&P 500 tickers")
    
    print("Fetching Nasdaq tickers...")
    nasdaq_tickers = get_nasdaq_tickers()
    print(f"Found {len(nasdaq_tickers)} Nasdaq tickers")
    
    # Combine and remove duplicates
    all_tickers = list(set(sp500_tickers + nasdaq_tickers))
    all_tickers.sort()
    
    # Filter tickers based on criteria
    filtered_tickers = filter_tickers(all_tickers)
    
    return filtered_tickers

def load_tickers():
    """Load tickers from JSON file, update if older than 1 day."""
    try:
        with open('tickers.json', 'r') as f:
            data = json.load(f)
            last_updated = datetime.strptime(data['last_updated'], '%Y-%m-%d %H:%M:%S')
            
            # Update if data is older than 1 day
            if datetime.now() - last_updated > timedelta(days=1):
                print("Ticker list is older than 1 day, updating...")
                return update_tickers_file()
            return data['tickers']
    except FileNotFoundError:
        print("No tickers file found, fetching fresh data...")
        return update_tickers_file()['tickers']
    except Exception as e:
        print(f"Error loading tickers: {str(e)}")
        return []

def _collect_candidate_tickers():
    """Return raw unique tickers from S&P-500 and Nasdaq helpers."""
    return sorted(set(get_sp500_tickers() + get_nasdaq_tickers()))

def _rebuild_validated_cache(batch_size: int = 100):
    """Validate raw tickers, save JSON cache, and return the valid list."""
    print("Validating ticker universe – this runs only when cache is missing or stale...")
    raw = _collect_candidate_tickers()
    valid, invalid = validate_ticker_batch(raw, batch_size=batch_size)

    data = {
        "generated": datetime.now().isoformat(),
        "total_raw": len(raw),
        "total_valid": len(valid),
        "total_invalid": invalid,
        "tickers": valid,
    }

    with open(VALIDATED_FILE, "w") as f:
        json.dump(data, f, indent=4)

    return valid

def load_valid_tickers(max_age_days: int = 1):
    """Return cached validated tickers, refreshing if older than *max_age_days*."""
    ensure_cache_dir()
    try:
        if os.path.exists(VALIDATED_FILE):
            with open(VALIDATED_FILE, "r") as f:
                data = json.load(f)
            gen_str = data.get("generated")
            if gen_str:
                try:
                    generated = datetime.fromisoformat(gen_str)
                    if datetime.now() - generated < timedelta(days=max_age_days):
                        return data["tickers"]
                except ValueError:
                    # malformed date, treat as fresh for now
                    return data["tickers"]
            else:
                # No timestamp – assume file is newly generated and accept
                return data["tickers"]
    except Exception:
        # Fall through to rebuild if file corrupt / unreadable
        pass

    # Need to rebuild
    return _rebuild_validated_cache() 

def clean_data_for_json(data):
    """
    Recursively cleans data to make it JSON serializable.
    Converts numpy types to native Python types.
    """
    if isinstance(data, dict):
        return {k: clean_data_for_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_data_for_json(i) for i in data]
    elif isinstance(data, (np.int_, np.intc, np.intp, np.int8,
                            np.int16, np.int32, np.int64, np.uint8,
                            np.uint16, np.uint32, np.uint64)):
        return int(data)
    elif isinstance(data, (np.floating, np.float16, np.float32, np.float64)):
        return float(data)
    elif isinstance(data, np.bool_):
        return bool(data)
    elif isinstance(data, (np.ndarray,)):
        return data.tolist()
    elif isinstance(data, pd.Timestamp):
        return data.isoformat()
    # Add other numpy/pandas type conversions as needed
    return data