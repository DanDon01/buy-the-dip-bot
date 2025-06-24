import json

# Load stock data to debug volume extraction
with open('cache/stock_data.json', 'r') as f:
    stock_data = json.load(f)

ticker = 'NVDA'
stock_record = stock_data[ticker].copy()

print(f"=== DEBUGGING VOLUME EXTRACTION FOR {ticker} ===")
print(f"Initial stock_record volume: {stock_record.get('volume', 'NOT_FOUND')}")
print(f"Initial avg_volume: {stock_record.get('avg_volume')}")

# Test the extraction logic from the API
if 'historical_data' in stock_record and isinstance(stock_record['historical_data'], dict):
    hist_data = stock_record['historical_data']
    print(f"✅ Historical data found with keys: {list(hist_data.keys())}")
    
    if 'volume' in hist_data and hist_data['volume']:
        print(f"✅ Volume history found with {len(hist_data['volume'])} entries")
        print(f"✅ Latest volume from history: {hist_data['volume'][-1]}")
        
        # This is the line that should set the volume
        stock_record['volume'] = hist_data['volume'][-1]
        print(f"✅ Set volume to: {stock_record['volume']} (type: {type(stock_record['volume'])})")
        
        # Test clean_data_for_json function
        from app import clean_data_for_json
        cleaned_record = clean_data_for_json(stock_record)
        print(f"After cleaning - volume: {cleaned_record.get('volume')} (type: {type(cleaned_record.get('volume'))})")
        
    else:
        print(f"❌ No volume in historical data or empty volume list")
        print(f"   hist_data.get('volume'): {hist_data.get('volume', 'NOT_FOUND')}")
else:
    print(f"❌ No historical data found")
    print(f"   'historical_data' in stock_record: {'historical_data' in stock_record}")
    if 'historical_data' in stock_record:
        print(f"   Type of historical_data: {type(stock_record['historical_data'])}") 