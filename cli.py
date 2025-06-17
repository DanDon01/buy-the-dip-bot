import argparse
from tracker import run_tracker
from data_collector import DataCollector
from utils import load_scores, save_top_scores_to_csv

def main():
    parser = argparse.ArgumentParser(description="🤖 Buy The Dip Bot CLI")

    parser.add_argument('--fetch', action='store_true', help="Fetch fresh stock data (API calls)")
    parser.add_argument('--score', action='store_true', help="Score previously cached data")
    parser.add_argument('--top', type=int, default=100, help="How many top scorers to keep (default: 100)")
    parser.add_argument('--update', action='store_true', help="Re-fetch detailed data for top scorers")
    parser.add_argument('--export', action='store_true', help="Export top N results to CSV")
    parser.add_argument('--debug', action='store_true', help="Print debug info")

    args = parser.parse_args()

    print("\n🎯 Starting Buy The Dip Bot CLI\n")

    if args.fetch:
        print("📡 Fetching fresh stock data (this may take time)...")
        dc = DataCollector()
        dc.fetch_all()
        print("✅ Data fetched and cached.\n")

    if args.score:
        print("📊 Scoring tickers...")
        run_tracker()
        print("✅ Scoring complete.\n")

    if args.export:
        print(f"📤 Exporting top {args.top} tickers...")
        scores = load_scores()
        save_top_scores_to_csv(scores, args.top)
        print(f"✅ Top {args.top} tickers exported to output/top_{args.top}.csv\n")

    if args.update:
        print("🔁 Re-fetching detailed info for top tickers...")
        dc = DataCollector()
        dc.update_top_scores(args.top)
        print("✅ Detailed updates complete.\n")

    print("👋 Done for now. Check the output folder!")

if __name__ == "__main__":
    main()
