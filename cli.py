#    Buy The Dip Bot CLI
# Command-line interface for the Buy The Dip Bot.
# Commands : --fetch, --score, --top, --update, --export, --debug, --filter
# --fetch : Fetch fresh stock data (API calls)
# --score : Score previously cached data
# --top : How many top scorers to keep (default: 100)
# --update : Re-fetch detailed data for top scorers
# --export : Export top N results to CSV
# --debug : Print debug info
# --filter : Run quick local filter to create top-500 list

import argparse
import os
import csv
import glob
from datetime import datetime
from tracker import StockTracker
from data_collector import DataCollector
from utils import load_scores, save_top_scores_to_csv
import yfinance as yf

def main():
    parser = argparse.ArgumentParser(description="🤖 Buy The Dip Bot CLI")

    parser.add_argument('--fetch', action='store_true', help="Fetch fresh stock data (API calls)")
    parser.add_argument('--score', action='store_true', help="Score previously cached data")
    parser.add_argument('--top', type=int, default=100, help="How many top scorers to keep (default: 100)")
    parser.add_argument('--update', action='store_true', help="Re-fetch detailed data for top scorers")
    parser.add_argument('--export', action='store_true', help="Export top N results to CSV")
    parser.add_argument('--debug', action='store_true', help="Print debug info")
    parser.add_argument('--filter', action='store_true', help='Run quick local filter to create top-500 list')

    args = parser.parse_args()

    print("\n🎯 Starting Buy The Dip Bot CLI\n")

    if args.fetch:
        print("🌐📡 API CALL: Fetching / updating stock data (weekly/daily routines)…")
        dc = DataCollector()
        dc.update_data()  # will run weekly & daily updates as needed
        print("✅ Data collection routine complete.\n")

    if args.filter:
        print('🔎 Running local filter to build top-500 list…')
        from run_filter import run_filter
        top500 = run_filter(verbose=True)
        pattern = 'filtered_top_500_*.csv'
        existing_files = glob.glob(pattern)
        latest_csv = max(existing_files, key=os.path.getmtime) if existing_files else None
        if latest_csv and args.debug:
            print(f'Filter CSV path: {latest_csv}')
        if args.debug:
            print(f"Using filter file: {latest_csv} containing {len(top500)} tickers")
        print(f'✅ Filter produced {len(top500)} tickers.\n')

    if args.score:
        print("🌐📡 API CALL: Updating scores (price + history) for the top-500 universe…")
        pattern = 'filtered_top_500_*.csv'
        files = glob.glob(pattern)
        if not files:
            from run_filter import run_filter
            top500 = run_filter(verbose=True)
        else:
            latest_csv = max(files, key=os.path.getmtime)
            with open(latest_csv) as f:
                top500 = [row['ticker'] for row in csv.DictReader(f)]
            if args.debug:
                print(f'Using filter file: {latest_csv} with {len(top500)} tickers')

        dc = DataCollector()
        dc.update_daily_scores(top500)

        tracker = StockTracker()  # will read the fresh daily_scores.json
        tracker.scan_stocks()
        print("✅ Score & scan complete.\n")

    if args.export:
        print(f"📤 Exporting top {args.top} tickers...")
        scores_json = load_scores()
        # Flatten the dict into a list of records with ticker key
        records = [
            {**{'ticker': t}, **info}
            for t, info in scores_json.get('scores', {}).items()
        ]
        if not records:
            print("⚠️  No score data found. Run --score first.")
        else:
            # Ensure output dir exists
            os.makedirs('output', exist_ok=True)
            save_top_scores_to_csv(records, args.top)
            print(f"✅ Exported top {args.top} tickers. Check output folder.\n")

    if args.update:
        print("🌐📡 API CALL: Re-fetching detailed info for top tickers…")
        dc = DataCollector()
        updated = dc.update_top_scores(args.top, recalc_scores=False)
        print(f"✅ Detailed updates complete for {len(updated) if updated else 0} tickers.\n")

    print("👋 Done for now. Check the output folder!")

if __name__ == "__main__":
    main()
