import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import json
import os
from utils import get_sp500_tickers, get_nasdaq_tickers, ensure_cache_dir, calculate_rsi
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

class DataCollector:
    def __init__(self):
        self.cache_dir = "cache"
        self.data_file = os.path.join(self.cache_dir, "stock_data.json")
        self.tickers_file = os.path.join(self.cache_dir, "filtered_tickers.json")
        self.scores_file = os.path.join(self.cache_dir, "daily_scores.json")
        self.last_update_file = os.path.join(self.cache_dir, "last_update.json")
        ensure_cache_dir()
    
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
                
                # Get basic info with timeout
                stock = yf.Ticker(cleaned_ticker)
                info = stock.info
                
                # Check if we got valid data
                if not info or 'regularMarketPrice' not in info:
                    print(f"✗ {ticker}: No market data available")
                    return None
                    
                current_price = info.get('regularMarketPrice')
                if not current_price or current_price <= 0:
                    print(f"✗ {ticker}: Invalid price data")
                    return None
                    
                # Get historical data with timeout
                hist = stock.history(period='1mo', interval='1d')
                if hist.empty:
                    print(f"✗ {ticker}: No historical data")
                    return None
                    
                # Calculate average volume
                avg_volume = hist['Volume'].mean()
                if avg_volume <= 0:
                    print(f"✗ {ticker}: Invalid volume data")
                    return None
                    
                # Get market cap
                market_cap = info.get('marketCap', 0)
                if market_cap <= 0:
                    print(f"✗ {ticker}: Invalid market cap")
                    return None
                    
                # Get exchange
                exchange = info.get('exchange', '')
                if not exchange:
                    print(f"✗ {ticker}: No exchange data")
                    return None
                    
                # Print success with data
                print(f"✓ {ticker}: Price=${current_price:.2f}, Vol={avg_volume:,.0f}, Cap=${market_cap:,.0f}, Ex={exchange}")
                
                return {
                    'ticker': ticker,
                    'current_price': current_price,
                    'avg_volume': avg_volume,
                    'market_cap': market_cap,
                    'exchange': exchange,
                    'historical_data': hist.to_dict('records')
                }
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"! {ticker}: Attempt {attempt + 1} failed - {str(e)}")
                    continue
                print(f"✗ {ticker}: Failed after {max_retries} attempts - {str(e)}")
                return None

    def process_ticker_batch(self, tickers, batch_size=10, delay=5):
        """Process tickers in small batches with proper delays."""
        all_stock_data = {}
        total_batches = (len(tickers) + batch_size - 1) // batch_size
        
        for batch_num, i in enumerate(range(0, len(tickers), batch_size), 1):
            batch = tickers[i:i + batch_size]
            print(f"\nProcessing batch {batch_num}/{total_batches} ({len(batch)} tickers)")
            
            # Process batch with ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_ticker = {
                    executor.submit(self._fetch_stock_data, ticker): ticker 
                    for ticker in batch
                }
                
                for future in as_completed(future_to_ticker):
                    ticker = future_to_ticker[future]
                    try:
                        data = future.result()
                        if data:
                            all_stock_data[ticker] = data
                    except Exception as e:
                        print(f"Error processing {ticker}: {str(e)}")
            
            # Save progress after each batch
            if all_stock_data:
                self.save_data(all_stock_data)
            
            # Add delay between batches
            if batch_num < total_batches:
                print(f"Waiting {delay} seconds before next batch...")
                time.sleep(delay)
            
        return all_stock_data

    def initial_filter_tickers(self):
        """Initial filtering of tickers with a test batch first."""
        print("Starting initial ticker filtering...")
        
        # Get all tickers
        sp500_tickers = get_sp500_tickers()
        nasdaq_tickers = get_nasdaq_tickers()
        all_tickers = list(set(sp500_tickers + nasdaq_tickers))
        
        print(f"Got {len(sp500_tickers)} S&P 500 tickers")
        print(f"Got {len(nasdaq_tickers)} Nasdaq tickers")
        print(f"Found {len(all_tickers)} unique tickers")
        
        # Process a small test batch first
        test_batch_size = 10
        print(f"\nTesting with first {test_batch_size} tickers...")
        test_data = self.process_ticker_batch(all_tickers[:test_batch_size], batch_size=5, delay=3)
        
        if not test_data:
            print("Test batch failed - no data collected. Please check API access.")
            return {}
        
        print(f"\nTest batch successful - collected data for {len(test_data)} tickers")
        print("Proceeding with full data collection...")
        
        # Process remaining tickers
        remaining_tickers = all_tickers[test_batch_size:]
        stock_data = self.process_ticker_batch(remaining_tickers)
        
        # Combine test and remaining data
        all_stock_data = {**test_data, **stock_data}
        
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
        """Calculate score for a single ticker."""
        try:
            # Convert historical data to DataFrame
            df = pd.DataFrame({
                'Close': data['historical_data']['close'],
                'Volume': data['historical_data']['volume'],
                'High': data['historical_data']['high'],
                'Low': data['historical_data']['low']
            }, index=pd.to_datetime(data['historical_data']['dates']))
            
            # Calculate metrics
            current_price = df['Close'].iloc[-1]
            high_5d = df['High'].max()
            drop_from_high = ((high_5d - current_price) / high_5d) * 100
            
            # Calculate RSI
            rsi = calculate_rsi(df['Close'], period=5).iloc[-1]
            
            # Calculate volume metrics
            avg_volume = df['Volume'].mean()
            last_volume = df['Volume'].iloc[-1]
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

if __name__ == "__main__":
    collector = DataCollector()
    collector.update_data() 