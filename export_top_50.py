import json
import csv

# --- Load scored data ---
with open("cache/daily_scores.json", "r") as f:
    data = json.load(f)

# --- Sort by score descending ---
scores = data["scores"]
sorted_scores = sorted(scores.items(), key=lambda x: x[1]["score"], reverse=True)

# --- Export top 50 ---
top_50 = sorted_scores[:50]

with open("output/top_50_scores.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Ticker", "Score", "Price", "RSI", "Drop %", "P/E", "Market Cap"])

    for ticker, details in top_50:
        breakdown = details.get("score_details", {})
        writer.writerow([
            ticker,
            details.get("score", ""),
            details.get("price", ""),
            breakdown.get("rsi", ""),
            breakdown.get("drop_pct", ""),
            breakdown.get("pe_ratio", ""),
            breakdown.get("market_cap", "")
        ])

print("✅ Top 50 exported to output/top_50_scores.csv")
