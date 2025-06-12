import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

def calculate_rsi(prices, period=14):
    """Calculate Relative Strength Index (RSI) for a series of prices."""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_stock_data(ticker, period="1y"):
    """Fetch stock data using yfinance."""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        return hist
    except Exception as e:
        print(f"Error fetching data for {ticker}: {str(e)}")
        return None

def calculate_score(stock_data):
    """Calculate a custom score based on various metrics."""
    if stock_data is None or len(stock_data) < 20:
        return 0
    
    # Calculate basic metrics
    current_price = stock_data['Close'].iloc[-1]
    high_52w = stock_data['High'].max()
    drop_from_high = ((high_52w - current_price) / high_52w) * 100
    rsi = calculate_rsi(stock_data['Close']).iloc[-1]
    
    # Basic scoring logic (can be enhanced)
    score = 0
    if drop_from_high > 20:  # Significant drop
        score += 30
    if 30 <= rsi <= 40:  # Oversold but not extremely
        score += 30
    
    return score

def save_to_json(data, filename):
    """Save data to a JSON file."""
    import json
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

def load_from_json(filename):
    """Load data from a JSON file."""
    import json
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {} 