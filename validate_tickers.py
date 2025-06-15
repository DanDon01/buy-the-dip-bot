import json
import os
import sys
from utils import (
    get_sp500_tickers,
    get_nasdaq_tickers,
    validate_ticker_batch,
    ensure_cache_dir,
)
from datetime import datetime

OUTPUT_FILE = os.path.join("cache", "validated_tickers.json")
BATCH_SIZE = 100  # adjust if you hit rate-limits


def collect_unique_tickers():
    """Return deduplicated list of potential tickers (S&P 500 + Nasdaq)."""
    sp500 = get_sp500_tickers()
    nasdaq = get_nasdaq_tickers()
    return sorted(set(sp500 + nasdaq))


def main():
    ensure_cache_dir()
    tickers = collect_unique_tickers()
    print(f"Found {len(tickers)} unique raw tickers – validating...")

    valid, invalid_count = validate_ticker_batch(tickers, batch_size=BATCH_SIZE)
    print(f"\nValidation complete → {len(valid)} valid, {invalid_count} invalid.")

    data = {
        "generated": datetime.now().isoformat(),
        "total_raw": len(tickers),
        "total_valid": len(valid),
        "total_invalid": invalid_count,
        "tickers": valid,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=4)

    print(f"Validated ticker list saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\nInterrupted – exiting.") 