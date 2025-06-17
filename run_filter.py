"""Quick post-processing filter for previously downloaded exchange-split
JSON files.  It applies some cheap numeric filters then keeps the *top_n*
tickers by market-cap.

The script can be run standalone:

    python run_filter.py               # generates filtered_top_500.csv

or it can be imported and the function ``run_filter`` called from the CLI.
"""

from __future__ import annotations

import csv
import json
import os
from typing import List, Dict, Any
from datetime import datetime

# crude numeric sanity filters – ultra-fast because all data is local JSON
MIN_MARKET_CAP = 5e7          # $50M minimum
MIN_VOLUME = 25_000           # Avoid illiquid names
MIN_PRICE = 2                 # Penny-stock floor
MAX_PRICE = 250               # Ignore ultra-pricey outliers
EXCHANGES = {"NYQ", "NMS", "NGM", "NCM"}

EXCHANGE_FOLDER = "cache/exchanges"

DATE_STR = datetime.now().strftime("%Y%m%d")
CSV_PATH_TEMPLATE = "filtered_top_{n}_" + DATE_STR + ".csv"


def _passes_basic_filters(info: Dict[str, Any]) -> bool:
    try:
        price = info["current_price"]
        volume = info["avg_volume"]
        cap = info["market_cap"]
        exchange = info["exchange"]
    except KeyError:
        return False

    return (
        exchange in EXCHANGES and
        cap >= MIN_MARKET_CAP and
        volume >= MIN_VOLUME and
        MIN_PRICE <= price <= MAX_PRICE
    )


def run_filter(top_n: int = 500, verbose: bool = False) -> List[str]:
    """Return a list of the *top_n* tickers after cheap local filtering.

    Also writes ``filtered_top_{n}.csv`` with the same records for manual
    inspection.  The function never makes network calls – it only looks at
    the JSON files produced earlier by ``DataCollector._save_by_exchange``.
    """

    if not os.path.isdir(EXCHANGE_FOLDER):
        raise FileNotFoundError(
            "Exchange JSON folder not found – run the data collector first."
        )

    records: List[Dict[str, Any]] = []

    for fn in os.listdir(EXCHANGE_FOLDER):
        if not fn.endswith(".json"):
            continue
        path = os.path.join(EXCHANGE_FOLDER, fn)
        try:
            with open(path) as f:
                data = json.load(f)
        except Exception as e:
            print(f"[WARN] Could not read {fn}: {e}")
            continue

        for ticker, info in data.items():
            if _passes_basic_filters(info):
                records.append(
                    {
                        "ticker": ticker,
                        "price": info["current_price"],
                        "volume": int(info["avg_volume"]),
                        "market_cap": int(info["market_cap"]),
                        "exchange": info["exchange"],
                    }
                )

    # Sort and keep top_n by market-cap
    records.sort(key=lambda x: x["market_cap"], reverse=True)
    top_records = records[:top_n]

    # Write CSV for eyeballing
    with open(CSV_PATH_TEMPLATE.format(n=top_n), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=top_records[0].keys())
        writer.writeheader()
        writer.writerows(top_records)

    if verbose:
        print(f"✅ Filtered {len(records)} → kept {len(top_records)}; saved {CSV_PATH_TEMPLATE.format(n=top_n)}")

    # Return just the ticker symbols
    return [r["ticker"] for r in top_records]


if __name__ == "__main__":
    run_filter(verbose=True)
