import json
import os

# Define your initial rough filters
MIN_MARKET_CAP = 5e7          # $50M minimum
MIN_VOLUME = 25_000           # Avoid illiquid stocks
MIN_PRICE = 2                 # Avoid penny stocks
MAX_PRICE = 250               # Ignore ultra-pricey outliers
EXCHANGES = ['NYQ', 'NMS', 'NGM', 'NCM']  # Stick to NYSE/NASDAQ variants

filtered_stocks = []

# Loop through your exchange files
exchange_folder = "cache/exchanges"
for filename in os.listdir(exchange_folder):
    if filename.endswith(".json"):
        with open(os.path.join(exchange_folder, filename)) as f:
            data = json.load(f)
        
        for ticker, info in data.items():
            try:
                price = info['current_price']
                volume = info['avg_volume']
                cap = info['market_cap']
                exchange = info['exchange']
                
                if (
                    exchange in EXCHANGES and
                    cap >= MIN_MARKET_CAP and
                    volume >= MIN_VOLUME and
                    MIN_PRICE <= price <= MAX_PRICE
                ):
                    filtered_stocks.append({
                        "ticker": ticker,
                        "price": price,
                        "volume": int(volume),
                        "market_cap": int(cap),
                        "exchange": exchange
                    })
            except Exception as e:
                print(f"[WARN] Skipping {ticker}: {e}")

# Sort by market cap descending for now
filtered_stocks.sort(key=lambda x: x["market_cap"], reverse=True)

# Save top 100 to CSV
import csv
with open("filtered_top_100.csv", "w", newline='') as f:
    writer = csv.DictWriter(f, fieldnames=filtered_stocks[0].keys())
    writer.writeheader()
    writer.writerows(filtered_stocks[:100])

print(f"✅ Filtered {len(filtered_stocks)} stocks; saved top 100 to filtered_top_100.csv")
