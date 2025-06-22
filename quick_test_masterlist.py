"""quick_test_masterlist.py
Run a mini-batch (first 10 validated tickers) through the MasterListManager
bulk-fetch path and print a summary so we can verify that at least one ticker
qualifies without waiting for the full 150-symbol batch.

Usage:
    python quick_test_masterlist.py
"""
from master_list import MasterListManager
from utils import load_valid_tickers

if __name__ == "__main__":
    mgr = MasterListManager()
    tickers = load_valid_tickers()[:10]
    print(f"▶️  Quick test on {len(tickers)} tickers: {', '.join(tickers)}")

    batch = mgr._bulk_fetch_basic_info(tickers)
    qualified = [r for r in batch if 'error' not in r and mgr._passes_master_list_filters(
        r, 1e8, 100000, ['NMS', 'NYQ', 'NGM', 'NCM']
    )]

    print("\n--- Summary ---")
    print(f"Fetched : {len(batch)}")
    print(f"Qualified: {len(qualified)}")
    if qualified:
        sample = ', '.join([q['ticker'] for q in qualified[:5]])
        print(f"Sample qualifying tickers: {sample}")
    else:
        print("No tickers qualified – check volume / exchange logic.") 