import pandas as pd
from datetime import datetime, timedelta
import os
from utils import get_stock_data, calculate_score, save_to_json, load_from_json

class StockTracker:
    def __init__(self):
        self.output_dir = "output"
        self.watchlist_file = "daily_watchlist.json"
        self.alerts_file = "alerts_log.csv"
        self.tickers_file = "tickers.csv"
        
        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def load_tickers(self):
        """Load tickers from CSV file."""
        try:
            return pd.read_csv(self.tickers_file)['ticker'].tolist()
        except FileNotFoundError:
            print(f"Warning: {self.tickers_file} not found. Using default S&P 500 tickers.")
            # You would typically fetch S&P 500 tickers here
            return ['AAPL', 'MSFT', 'GOOGL']  # Placeholder
    
    def scan_stocks(self):
        """Main scanning function."""
        tickers = self.load_tickers()
        results = []
        
        for ticker in tickers:
            stock_data = get_stock_data(ticker)
            if stock_data is not None:
                score = calculate_score(stock_data)
                current_price = stock_data['Close'].iloc[-1]
                
                results.append({
                    'ticker': ticker,
                    'price': current_price,
                    'score': score,
                    'date': datetime.now().strftime('%Y-%m-%d')
                })
                
                # Check for "Perfect Buy" conditions
                if score >= 50:  # Example threshold
                    self.log_alert(ticker, score, current_price)
        
        return pd.DataFrame(results)
    
    def update_watchlist(self, new_results):
        """Update the 7-day watchlist."""
        watchlist = load_from_json(self.watchlist_file)
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Add new results
        watchlist[today] = new_results.to_dict('records')
        
        # Remove entries older than 7 days
        cutoff_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        watchlist = {k: v for k, v in watchlist.items() if k > cutoff_date}
        
        save_to_json(watchlist, self.watchlist_file)
    
    def log_alert(self, ticker, score, price):
        """Log "Perfect Buy" alerts."""
        alert = {
            'ticker': ticker,
            'score': score,
            'price': price,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        df = pd.DataFrame([alert])
        if os.path.exists(self.alerts_file):
            df.to_csv(self.alerts_file, mode='a', header=False, index=False)
        else:
            df.to_csv(self.alerts_file, index=False)
    
    def run(self):
        """Main execution function."""
        print(f"Starting scan at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Scan stocks
        results = self.scan_stocks()
        
        # Save daily results
        output_file = os.path.join(self.output_dir, f"scan_{datetime.now().strftime('%Y%m%d')}.csv")
        results.to_csv(output_file, index=False)
        
        # Update watchlist
        self.update_watchlist(results)
        
        print(f"Scan complete. Results saved to {output_file}")
        print(f"Top 5 stocks by score:")
        print(results.nlargest(5, 'score')[['ticker', 'score', 'price']])

if __name__ == "__main__":
    tracker = StockTracker()
    tracker.run() 