import pandas as pd
from datetime import datetime, timedelta
import os
import json
from utils import calculate_rsi
from data_collector import DataCollector
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils import ensure_cache_dir

class StockTracker:
    def __init__(self):
        self.output_dir = "output"
        self.watchlist_file = os.path.join(self.output_dir, "watchlist.json")
        self.alerts_file = os.path.join(self.output_dir, "alerts.json")
        self.cache_dir = "cache"
        ensure_cache_dir()
        
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
        scores = []
        for ticker, data in scores_data['scores'].items():
            if data['score'] >= 50:  # Only include stocks with score >= 50
                scores.append({
                    'ticker': ticker,
                    'price': data['price'],
                    'score': data['score'],
                    'score_details': data['score_details'],
                    'timestamp': data['timestamp']
                })
        
        if not scores:
            print("\nNo stocks currently meet the buying criteria.")
            return pd.DataFrame()
        
        # Convert to DataFrame and sort by score
        df = pd.DataFrame(scores)
        df = df.sort_values('score', ascending=False)
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d')
        output_file = os.path.join(self.output_dir, f"scan_{timestamp}.csv")
        df.to_csv(output_file, index=False)
        
        # Update watchlist with new opportunities
        self._update_watchlist(df)
        
        # Print results
        print(f"\nFound {len(df)} potential buying opportunities!")
        print("\nTop 5 stocks by score:")
        for _, row in df.head().iterrows():
            print(f"\n{row['ticker']} (Score: {row['score']})")
            print(f"Current Price: ${row['price']:.2f}")
            print("Score Breakdown:")
            for metric, details in row['score_details'].items():
                print(f"  {metric.replace('_', ' ').title()}: {details['points']}/{details['max_points']} points")
                print(f"    Value: {details['value']} (Threshold: {details['threshold']})")
        
        print(f"\nFull results saved to: {output_file}")
        return df
    
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

if __name__ == "__main__":
    tracker = StockTracker()
    tracker.scan_stocks() 