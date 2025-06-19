from flask import Flask, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
import pandas as pd
from utils import load_scores
import yfinance as yf
import subprocess
import sys

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})  # Allow all origins for API routes

def load_processed_data():
    """Load and merge score data with historical data."""
    try:
        scores_data = load_scores()
        
        data_file = os.path.join("cache", "stock_data.json")
        with open(data_file, 'r') as f:
            historical_data = json.load(f)

        if not scores_data or not historical_data:
            return None
        
        records = []
        for ticker, data in scores_data.get('scores', {}).items():
            if ticker in historical_data:
                record = {
                    'ticker': ticker,
                    'price': data['price'],
                    'score': data['score'],
                    'score_details': data['score_details'],
                    'timestamp': data['timestamp'],
                    'history': historical_data[ticker].get('historical_data')
                }
                records.append(record)
        
        df = pd.DataFrame(records)
        df = df.sort_values('score', ascending=False)
        return df
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"Error loading processed data: {e}")
        return None

@app.route('/api/stats')
def get_stats():
    """API endpoint for summary statistics."""
    df = load_processed_data()
    if df is None:
        return jsonify({'error': 'No data available'}), 404
        
    stats = {
        'total_stocks': len(df),
        'avg_score': float(df['score'].mean()),
        'top_scorer': df.iloc[0]['ticker'],
        'top_score': float(df.iloc[0]['score']),
        'last_update': pd.to_datetime(df['timestamp']).max().strftime('%Y-%m-%d %H:%M')
    }
    return jsonify(stats)

@app.route('/api/stocks')
def get_stocks():
    """API endpoint for all stock data."""
    df = load_processed_data()
    if df is None:
        return jsonify({'error': 'No data available'}), 404
    
    return jsonify(df.to_dict('records'))

@app.route('/api/stock/<ticker>')
def get_stock_detail(ticker):
    """API endpoint for individual stock data."""
    df = load_processed_data()
    if df is None:
        return jsonify({'error': 'No data available'}), 404
    
    stock_data = df[df['ticker'] == ticker.upper()]
    if stock_data.empty:
        return jsonify({'error': f'Stock {ticker} not found'}), 404
    
    stock_record = stock_data.to_dict('records')[0]
    
    # Convert history data to expected format if it exists
    if stock_record.get('history') and isinstance(stock_record['history'], dict):
        history_dict = stock_record['history']
        if 'close' in history_dict and 'dates' in history_dict:
            # Convert to array of objects format
            dates = history_dict['dates']
            prices = history_dict['close']
            stock_record['history'] = [
                {'date': date, 'price': price} 
                for date, price in zip(dates, prices)
            ]
        else:
            # If data format is unexpected, set to empty array
            stock_record['history'] = []
    
    return jsonify(stock_record)

def _to_native_py_type(val):
    """Converts numpy types to native Python types for JSON serialization."""
    if val is None:
        return None
    if pd.isna(val):
        return None
    if isinstance(val, (pd.Timestamp, datetime)):
        return val.isoformat()
    if hasattr(val, 'item'):
        return val.item()
    return val

@app.route('/api/stock_details/<ticker>')
def get_stock_extra_details(ticker):
    """API endpoint for fetching extra details for a stock."""
    try:
        print(f"Fetching details for ticker: {ticker}")
        
        # Add timeout to yfinance calls
        import requests
        session = requests.Session()
        session.timeout = 10  # 10 second timeout
        
        stock = yf.Ticker(ticker, session=session)
        
        # Add timeout and error handling for the info call
        try:
            print(f"Calling yfinance info for {ticker}...")
            info = stock.info
            print(f"Successfully got info for {ticker}, keys: {list(info.keys())[:10] if info else 'None'}")
        except requests.exceptions.Timeout:
            print(f"Timeout error for {ticker}")
            return jsonify({'error': f'Timeout fetching data for {ticker}'}), 504
        except requests.exceptions.RequestException as req_error:
            print(f"Request error for {ticker}: {req_error}")
            return jsonify({'error': f'Network error fetching data for {ticker}'}), 503
        except Exception as info_error:
            print(f"Failed to get info for {ticker}: {info_error}")
            return jsonify({'error': f'Failed to fetch data for {ticker} from yfinance'}), 500

        # More robust validation
        if not info or not isinstance(info, dict):
            print(f"Empty or invalid info for {ticker} from yfinance.")
            return jsonify({'error': f'No data available for {ticker}'}), 404

        # Extract details with better error handling
        details = {}
        try:
            details['52_week_high'] = _to_native_py_type(info.get('fiftyTwoWeekHigh'))
            details['52_week_low'] = _to_native_py_type(info.get('fiftyTwoWeekLow'))
            details['forward_pe'] = _to_native_py_type(info.get('forwardPE'))
            details['dividend_yield'] = _to_native_py_type(info.get('dividendYield'))
            details['market_cap'] = _to_native_py_type(info.get('marketCap'))
            
            print(f"Successfully extracted details for {ticker}: {details}")
        except Exception as extract_error:
            print(f"Error extracting details for {ticker}: {extract_error}")
            return jsonify({'error': f'Error processing data for {ticker}'}), 500
        
        return jsonify(details)
    except Exception as e:
        # This will catch network errors, timeouts, or other unexpected yfinance issues
        print(f"Generic error fetching extra details for {ticker} from yfinance: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Unable to fetch details for {ticker}'}), 500

@app.route('/api/tasks/run_fetch', methods=['POST'])
def run_fetch_task():
    """Endpoint to trigger the --fetch CLI command."""
    try:
        # Using sys.executable to ensure we use the same python interpreter
        subprocess.Popen([sys.executable, 'cli.py', '--fetch'])
        return jsonify({'message': 'Fetch task started successfully. This may take a few minutes.'}), 202
    except Exception as e:
        return jsonify({'error': f'Failed to start fetch task: {e}'}), 500

@app.route('/api/tasks/run_score', methods=['POST'])
def run_score_task():
    """Endpoint to trigger the --score CLI command."""
    try:
        subprocess.Popen([sys.executable, 'cli.py', '--score'])
        return jsonify({'message': 'Score task started successfully. This may take several minutes.'}), 202
    except Exception as e:
        return jsonify({'error': f'Failed to start score task: {e}'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)  # Running on a different port (5001) to avoid conflicts with React dev server 