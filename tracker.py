import pandas as pd
from datetime import datetime, timedelta
import os
import json
from utils import (
    calculate_rsi,
    ensure_cache_dir,
    ensure_output_dir,
    CACHE_DIR,
    OUTPUT_DIR,
)
from data_collector import DataCollector
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from yahooquery import Ticker

class StockTracker:
    def __init__(self):
        self.output_dir = OUTPUT_DIR
        self.watchlist_file = os.path.join(self.output_dir, "watchlist.json")
        self.alerts_file = os.path.join(self.output_dir, "alerts.json")
        self.cache_dir = CACHE_DIR
        ensure_cache_dir()
        ensure_output_dir()
        
        # Initialize data collector
        self.collector = DataCollector()
        
        # Load or initialize watchlist and alerts
        self.watchlist = self._load_json(self.watchlist_file, {'tickers': [], 'last_updated': None})
        self.alerts = self._load_json(self.alerts_file, {'alerts': [], 'last_updated': None})
    
    def _load_json(self, filepath, default=None):
        """Load JSON file or return default if not exists."""
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            if default is not None:
                with open(filepath, 'w') as f:
                    json.dump(default, f, indent=4)
                return default
            return None
    
    def _save_json(self, filepath, data):
        """Save data to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
    
    def _load_data(self):
        """Load current market data and scores."""
        try:
            # Update data if needed
            self.collector.update_data()
            
            # Load current scores
            with open(os.path.join(self.cache_dir, "daily_scores.json"), 'r') as f:
                scores_data = json.load(f)
            
            # Load market data
            with open(os.path.join(self.cache_dir, "stock_data.json"), 'r') as f:
                market_data = json.load(f)
            
            return scores_data, market_data
            
        except FileNotFoundError as e:
            print(f"Error: Required data files not found. Please run data collection first.")
            print(f"Missing file: {str(e)}")
            return None, None
    
    def scan_stocks(self):
        """Scan stocks for buying opportunities using cached data."""
        print("\nStarting stock scan...")
        
        # Load current data
        scores_data, market_data = self._load_data()
        if not scores_data or not market_data:
            return pd.DataFrame()
        
        # Convert scores to DataFrame
        rows = []
        for ticker, data in scores_data['scores'].items():
            year_high = market_data.get(ticker, {}).get('year_high')
            pct_below = None
            if year_high and year_high > 0:
                pct_below = ((year_high - data['price']) / year_high) * 100

            rows.append({
                'ticker': ticker,
                'price': data['price'],
                'score': data['score'],
                'score_details': data['score_details'],
                'year_high': year_high,
                '%_below_high': round(pct_below, 2) if pct_below is not None else None,
                'timestamp': data['timestamp']
            })

        if not rows:
            print("No scored tickers found. Run update first.")
            return pd.DataFrame()

        df_all = pd.DataFrame(rows).sort_values('score', ascending=False)

        # Watchlist threshold
        watch_df = df_all[df_all['score'] >= 50]

        # Ensure at least top 5 rows are shown
        top_display = df_all.head(5)
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d')
        output_file = os.path.join(self.output_dir, f"scan_{timestamp}.csv")
        df_all.to_csv(output_file, index=False)
        
        # Update watchlist with new opportunities
        self._update_watchlist(watch_df)
        
        # Print results
        print(f"\nFound {len(watch_df)} potential buying opportunities!")
        print("\nTop 5 stocks by score:")
        for _, row in top_display.iterrows():
            print(f"\n{row['ticker']} (Score: {row['score']})")
            print(f"Current Price: ${row['price']:.2f}")
            if pd.notna(row.get('year_high')):
                print(f"52-Wk High:  ${row['year_high']:.2f}  |  % Below High: {row['%_below_high']:.1f}%")
            print("Score Breakdown:")
            for metric, details in row['score_details'].items():
                if isinstance(details, dict):
                    pts = details.get('points', details.get('value', ''))
                    max_pts = details.get('max_points', '')
                    thresh = details.get('threshold', '')
                    val = details.get('value', '')
                    print(f"  {metric.replace('_', ' ').title()}: {pts}/{max_pts} points")
                    if val or thresh:
                        print(f"    Value: {val} (Threshold: {thresh})")
                else:
                    print(f"  {metric.replace('_', ' ').title()}: {details} points")
        
        print(f"\nFull results saved to: {output_file}")
        return watch_df
    
    def _update_watchlist(self, opportunities_df):
        """Update watchlist with new opportunities."""
        current_time = datetime.now().isoformat()
        
        # Convert opportunities to watchlist format
        new_opportunities = []
        for _, row in opportunities_df.iterrows():
            opportunity = {
                'ticker': row['ticker'],
                'price': row['price'],
                'score': row['score'],
                'score_details': row['score_details'],
                'first_seen': current_time,
                'last_updated': current_time,
                'status': 'active'
            }
            new_opportunities.append(opportunity)
        
        # Update watchlist
        self.watchlist['tickers'].extend(new_opportunities)
        self.watchlist['last_updated'] = current_time
        
        # Save updated watchlist
        self._save_json(self.watchlist_file, self.watchlist)
        
        # Create alerts for new opportunities
        self._create_alerts(new_opportunities)
    
    def _create_alerts(self, new_opportunities):
        """Create alerts for new opportunities."""
        current_time = datetime.now().isoformat()
        
        # Create alerts for each new opportunity
        for opp in new_opportunities:
            alert = {
                'ticker': opp['ticker'],
                'price': opp['price'],
                'score': opp['score'],
                'score_details': opp['score_details'],
                'timestamp': current_time,
                'type': 'new_opportunity',
                'message': f"New buying opportunity: {opp['ticker']} (Score: {opp['score']})"
            }
            self.alerts['alerts'].append(alert)
        
        # Update alerts timestamp
        self.alerts['last_updated'] = current_time
        
        # Save updated alerts
        self._save_json(self.alerts_file, self.alerts)

    def _save_by_exchange(self, data, out_dir="cache/exchanges"):
        os.makedirs(out_dir, exist_ok=True)

        groups = {}
        for t, d in data.items():
            ex = d.get("exchange", "UNK")
            groups.setdefault(ex, {})[t] = d

        for ex, tickers in groups.items():
            path = os.path.join(out_dir, f"{ex}.json")
            with open(path, "w") as f:
                json.dump(tickers, f, indent=4)

    def filter_tickers(self, data):
        # Implementation of filter_tickers method (placeholder)
        pass

    def _fetch_history(self, ticker):
        try:
            hist = Ticker(ticker, timeout=8).history(period="1mo", interval="1d")
            ...
        except Exception:
            return None

def fetch_price_bulk(symbols):
    t = Ticker(" ".join(symbols), asynchronous=False, progress=False)
    return t.price  # dict keyed by symbol

if __name__ == "__main__":
    tracker = StockTracker()
    tracker.scan_stocks() 

    BULK = 200
    for batch in chunks(remaining_tickers, BULK):
        price_map = fetch_price_bulk(batch)
        # loop over batch, read history only for the symbols
        # that passed the price check
        for symbol, info in survivors:
            print(f"    [{symbol}] fetching history…", end="", flush=True)
            hist = self._fetch_history(symbol)
            if hist is None or hist.empty:
                self._mark_bad(symbol)
                print(f"✗ {symbol}: no history")
                time.sleep(HISTORY_RATE_LIMIT)
                continue
            record = self._assemble_record(symbol, info, hist)
            all_stock_data[symbol] = record
            print(" done")
            time.sleep(HISTORY_RATE_LIMIT)
        time.sleep(10)        # cool-down between bulks 
