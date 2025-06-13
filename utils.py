import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import json
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
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period, interval='1d')[['Close', 'Volume']]
        
        if len(hist) < 3:
            return None
        
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

def calculate_score(stock_data):
    """Calculate a custom score based on various metrics."""
    if stock_data is None or len(stock_data) < 3:
        return 0, {}
    
    try:
        # Calculate basic metrics
        current_price = stock_data['Close'].iloc[-1]
        high_5d = stock_data['Close'].max()
        drop_from_high = ((high_5d - current_price) / high_5d) * 100
        
        # Calculate RSI on a smaller window
        rsi = calculate_rsi(stock_data['Close'], period=5).iloc[-1]
        
        # Calculate volume metrics
        avg_volume = stock_data['Volume'].mean()
        last_volume = stock_data['Volume'].iloc[-1]
        volume_ratio = (last_volume / avg_volume) * 100
        
        # Initialize scoring components
        score = 0
        score_details = {
            'price_drop': {
                'value': f"{drop_from_high:.1f}%",
                'points': 0,
                'threshold': ">5%",
                'max_points': 30
            },
            'rsi': {
                'value': f"{rsi:.1f}",
                'points': 0,
                'threshold': "25-35",
                'max_points': 30
            },
            'volume': {
                'value': f"{volume_ratio:.1f}% of avg",
                'points': 0,
                'threshold': ">150%",
                'max_points': 20
            }
        }
        
        # Score price drop
        if drop_from_high > 5:
            score += 30
            score_details['price_drop']['points'] = 30
        
        # Score RSI
        if 25 <= rsi <= 35:
            score += 30
            score_details['rsi']['points'] = 30
        
        # Score volume
        if last_volume > avg_volume * 1.5:
            score += 20
            score_details['volume']['points'] = 20
        
        return score, score_details
    except Exception as e:
        print(f"Error calculating score: {str(e)}")
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
        stock = yf.Ticker(ticker)
        # Only fetch 1 day of data for validation
        hist = stock.history(period='1d', interval='1d')[['Close']]
        return len(hist) > 0
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
            return cached_data['data']
    
    # If not in cache or expired, fetch from API
    try:
        with suppress_output():
            stock = yf.Ticker(ticker)
            info = stock.info
            data = {
                'ticker': ticker,
                'market_cap': info.get('marketCap', 0),
                'volume': info.get('averageVolume', 0),
                'exchange': info.get('exchange', ''),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', '')
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
    except Exception:
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