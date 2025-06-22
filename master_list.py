#!/usr/bin/env python3
"""
Hierarchical Master List Management System

Implements a 3-tier architecture for efficient stock screening:
- Tier 1: Master List (~2000 quality stocks from 6969 validated tickers)
- Tier 2: Screening Lists (Top N ranked candidates from master list)
- Tier 3: Deep Analysis (Full data collection for final picks)

This solves the "top N" problem by providing meaningful rankings at each tier.
"""

import json
import pandas as pd
import math
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import signal
import importlib
import sys
from itertools import islice

# Finnhub integration -----------------------------------------
from dotenv import load_dotenv
load_dotenv()

try:
    from collectors.finnhub_collector import FinnhubCollector, RateLimitError
except Exception:
    FinnhubCollector = None  # graceful fallback

# Ensure RateLimitError is defined even when Finnhub module unavailable
try:
    RateLimitError  # type: ignore
except NameError:
    class RateLimitError(RuntimeError):
        """Raised when any provider hits an HTTP 429 rate limit."""
        pass

from utils import (
    load_valid_tickers, get_stock_info, ensure_cache_dir,
    save_cache, load_cache, suppress_output,
    get_cache_key, _stock_info_cache, CACHE_EXPIRY
)
from yahooquery import Ticker

# Constants
MASTER_LIST_FILE = "cache/master_list.json"
SCREENING_LISTS_DIR = "cache/screening_lists"
MASTER_LIST_MAX_AGE_DAYS = 30  # Refresh monthly
SCREENING_LIST_MAX_AGE_DAYS = 1  # Refresh daily


class MasterListManager:
    """Manages the hierarchical stock screening system."""
    
    def __init__(self):
        self.ensure_directories()
        # Optional Finnhub collector for bulk basic info
        self._finnhub = None
        if FinnhubCollector is not None:
            try:
                self._finnhub = FinnhubCollector()
                print("📡 MasterListManager: Finnhub enabled for basic info fetch.")
            except Exception as e:
                print(f"⚠️  Finnhub not available ({e}). Falling back to Yahoo quote v7.")
                self._finnhub = None
    
    def ensure_directories(self):
        """Ensure all necessary directories exist."""
        ensure_cache_dir()
        Path(SCREENING_LISTS_DIR).mkdir(parents=True, exist_ok=True)
    
    def is_master_list_fresh(self) -> bool:
        """Check if master list exists and is fresh."""
        if not Path(MASTER_LIST_FILE).exists():
            return False
        
        try:
            with open(MASTER_LIST_FILE, 'r') as f:
                data = json.load(f)
            
            created = datetime.fromisoformat(data.get('created', '2000-01-01'))
            age = datetime.now() - created
            return age.days < MASTER_LIST_MAX_AGE_DAYS
        except Exception:
            return False
    
    def get_master_list_stats(self) -> Optional[Dict]:
        """Get statistics about the current master list."""
        if not Path(MASTER_LIST_FILE).exists():
            return None
        
        try:
            with open(MASTER_LIST_FILE, 'r') as f:
                data = json.load(f)
            
            created = datetime.fromisoformat(data.get('created', '2000-01-01'))
            age_days = (datetime.now() - created).days
            
            return {
                'total_stocks': len(data.get('stocks', [])),
                'created': data.get('created'),
                'age_days': age_days,
                'criteria': data.get('filter_criteria', {}),
                'fresh': age_days < MASTER_LIST_MAX_AGE_DAYS
            }
        except Exception:
            return None
    
    def build_master_list(self, 
                         min_market_cap: float = 1e8,     # $100M
                         min_volume: int = 100000,        # 100K daily volume
                         exchanges: List[str] = None,
                         target_size: int = 2000) -> Dict:
        """
        Build Tier 1: Master List of ~2000 quality stocks from validated universe.
        """
        if exchanges is None:
            exchanges = ['NMS', 'NYQ', 'NGM']  # NASDAQ and NYSE variants
        
        print("🏗️  BUILDING TIER 1: MASTER LIST")
        print("=" * 50)
        print(f"Target size: ~{target_size:,} quality stocks")
        print(f"Criteria:")
        print(f"  • Market Cap > ${min_market_cap/1e6:.0f}M")
        print(f"  • Daily Volume > {min_volume:,}")
        print(f"  • Exchanges: {', '.join(exchanges)}")
        
        # Get validated ticker universe
        print(f"\n📊 Loading validated ticker universe...")
        all_tickers = load_valid_tickers()
        print(f"   Found {len(all_tickers):,} validated tickers")

        # If there is a checkpoint file, treat its tickers as "fresh"
        # Initialize even when no checkpoint exists to avoid NameError later
        existing_fresh: Dict[str, Dict] = {}
        if Path(MASTER_LIST_FILE).exists():
            with open(MASTER_LIST_FILE) as f:
                ckpt = json.load(f)
            existing_fresh = {s['ticker']: s for s in ckpt.get('stocks', [])}
            print(f"   Resuming from checkpoint – {len(existing_fresh):,} already done")

        processed = 0
        processed_symbols = set()
        processed_skip = set()

        for rec in existing_fresh.values():
            processed_skip.add(rec["ticker"])
            ts = rec.get("timestamp")
            if ts:
                try:
                    ts_dt = datetime.fromisoformat(ts)
                    if ts_dt > datetime.now() - timedelta(hours=48):
                        existing_fresh[rec["ticker"]] = rec
                except Exception:
                    pass

        remaining_tickers = [
            t for t in all_tickers
            if t not in processed_skip
               and t not in existing_fresh
               and t not in processed_symbols
        ]
        print(f"   Remaining to process: {len(remaining_tickers):,}")

        if not remaining_tickers:
            print("✅ Master list already up to date – nothing to process.")
            return existing_fresh
        
        # ---------- NEW HIGH-THROUGHPUT BULK MODE ----------
        try:
            new_data = self._build_master_list_bulk(remaining_tickers, min_market_cap, min_volume, exchanges, target_size)

            # Merge with previously skipped fresh records
            if existing_fresh and new_data.get("stocks"):
                merged_dict = {rec["ticker"]: rec for rec in new_data.get("stocks", [])}
                merged_dict.update(existing_fresh)  # keep fresh ones
                new_data["stocks"] = list(merged_dict.values())
                if "stats" in new_data:
                    new_data["stats"]["total_in_master_list"] = len(new_data["stocks"])

                with open(MASTER_LIST_FILE, "w") as f:
                    json.dump(new_data, f, indent=2)

            return new_data
        except RateLimitError as rl_err:
            print(f"❌ Master list build aborted due to rate-limit: {rl_err}")
            raise
        except Exception as e:
            print(f"⚠️  Bulk mode failed with error: {e}. Falling back to legacy per-ticker mode…")
            return {}  # Fallback stub
        
        # ---------- Legacy per-ticker mode below (kept for fallback) ----------
    
    def _get_stock_basic_info(self, ticker: str) -> Optional[Dict]:
        """Get basic stock info needed for master list filtering."""
        try:
            # Use a specialized version that doesn't suppress output to avoid I/O errors
            result = self._get_stock_info_no_suppress(ticker)
            if isinstance(result, dict) and 'error' not in result:
                # Add basic quality metrics for ranking
                result['quality_score'] = self._calculate_basic_quality_score(result)
                return result
            elif isinstance(result, dict) and 'error' in result:
                # Return error info for detailed reporting
                return result
            return None
        except Exception as e:
            return {'error': f'Exception in _get_stock_basic_info: {str(e)[:100]}'}
    
    def _get_stock_info_no_suppress(self, ticker: str) -> Optional[Dict]:
        """Get basic stock info without output suppression to avoid I/O errors."""
        cache_key = get_cache_key(ticker, 'info')
        current_time = datetime.now()
        
        # Check cache first
        if cache_key in _stock_info_cache:
            cached_data = _stock_info_cache[cache_key]
            if current_time - cached_data['timestamp'] < CACHE_EXPIRY:
                data = cached_data['data'].copy()
                data['_from_cache'] = True
                data['_cache_age_hours'] = (current_time - cached_data['timestamp']).total_seconds() / 3600
                return data
        
        # If not in cache or expired, fetch from API with timeout and error handling
        try:
            # Create ticker with timeout to prevent hanging
            stock = Ticker(ticker, timeout=10)  # 10 second timeout
            
            # Get data with error checking
            summary_raw = stock.summary_detail
            price_raw = stock.price
            
            # Validate API response structure
            if not isinstance(summary_raw, dict) or not isinstance(price_raw, dict):
                return {'error': f'Invalid API response structure: summary={type(summary_raw)}, price={type(price_raw)}'}
                
            summary = summary_raw.get(ticker, {})
            price = price_raw.get(ticker, {})
            
            # Check if we got error messages instead of data
            if isinstance(summary, str):
                if 'Invalid Crumb' in summary or 'crumb' in summary.lower():
                    return {'error': f'Invalid Crumb (Yahoo auth expired): {ticker}'}
                return {'error': f'API returned error for summary: {summary[:100]}'}
            if isinstance(price, str):
                if 'Invalid Crumb' in price or 'crumb' in price.lower():
                    return {'error': f'Invalid Crumb (Yahoo auth expired): {ticker}'}
                return {'error': f'API returned error for price: {price[:100]}'}
                
            info = {**summary, **price}

            # Validate essential data is present
            market_cap = info.get('marketCap', 0)
            volume = info.get('averageVolume', info.get('averageDailyVolume10Day', 0))
            exchange = info.get('exchange', info.get('exchangeName', ''))
            
            if not market_cap or not volume or not exchange:
                return {'error': f'Missing essential data: MC={market_cap}, Vol={volume}, Ex={exchange}'}

            data = {
                'ticker': ticker,
                'market_cap': market_cap,
                'volume': volume,
                'exchange': exchange,
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                '_from_cache': False,
                '_api_call_time': current_time.isoformat()
            }
            
            # Update cache
            _stock_info_cache[cache_key] = {
                'timestamp': current_time,
                'data': data
            }
            
            # Save cache periodically (every 50 updates to reduce I/O)
            if len(_stock_info_cache) % 50 == 0:
                try:
                    save_cache(_stock_info_cache)
                except Exception:
                    pass  # Don't fail on cache save errors
            
            return data
            
        except KeyboardInterrupt:
            # Allow graceful interruption
            raise
        except Exception as e:
            # Return detailed error information
            error_msg = str(e)
            if 'Invalid Crumb' in error_msg or 'crumb' in error_msg.lower():
                return {'error': f'Invalid Crumb (Yahoo auth expired): {ticker}'}
            elif 'timeout' in error_msg.lower():
                return {'error': f'Timeout after 10s: {error_msg[:80]}'}
            elif 'rate limit' in error_msg.lower() or '429' in error_msg:
                return {'error': f'RATE LIMIT HIT: {error_msg[:80]}'}
            elif 'connection' in error_msg.lower():
                return {'error': f'Connection error: {error_msg[:80]}'}
            else:
                return {'error': f'API error: {error_msg[:80]}'}
    
    def _passes_master_list_filters(self, stock_info: Dict, 
                                   min_market_cap: float, 
                                   min_volume: int, 
                                   exchanges: List[str]) -> bool:
        """Check if stock passes master list filters."""
        try:
            return (
                stock_info.get('market_cap', 0) >= min_market_cap and
                stock_info.get('volume', 0) >= min_volume and
                stock_info.get('exchange', '') in exchanges and
                stock_info.get('ticker', '').replace('.', '').isalnum()  # Valid ticker format
            )
        except Exception:
            return False
    
    def _calculate_basic_quality_score(self, stock_info: Dict) -> float:
        """Calculate a basic quality score for master list ranking."""
        score = 0.0
        
        # Market cap score (larger = better, but with diminishing returns)
        market_cap = stock_info.get('market_cap', 0)
        if market_cap > 0:
            # Log scale: $100M=1, $1B=2, $10B=3, $100B=4, $1T=5
            import math
            score += min(5.0, math.log10(market_cap / 1e8))
        
        # Volume score (higher volume = more liquid)
        volume = stock_info.get('volume', 0)
        if volume > 0:
            # Log scale: 100K=1, 1M=2, 10M=3
            import math
            score += min(3.0, math.log10(volume / 1e5))
        
        # Exchange preference (NYSE/NASDAQ main exchanges preferred)
        exchange = stock_info.get('exchange', '')
        if exchange in ['NYQ', 'NMS']:  # Main boards
            score += 1.0
        elif exchange in ['NGM']:  # NASDAQ Global Market
            score += 0.5
        
        return score
    
    def _rank_stocks_for_master_list(self, stocks: List[Dict]) -> List[Dict]:
        """Rank stocks by quality score for master list selection."""
        # Sort by quality score (descending) then by market cap (descending)
        return sorted(stocks, 
                     key=lambda x: (x.get('quality_score', 0), x.get('market_cap', 0)), 
                     reverse=True)
    
    def _chunked(self, iterable, size: int):
        """Yield successive chunks from *iterable* of length *size*."""
        it = iter(iterable)
        while chunk := list(islice(it, size)):
            yield chunk

    def _bulk_fetch_basic_info(self, tickers: List[str]) -> List[Dict]:
        """Fetch basic info for a batch of *tickers*.

        • If Finnhub is available → use `FinnhubCollector.get_stock_snapshot`.
        • Otherwise → fall back to Yahoo v7 quote endpoint (existing logic).
        """

        if self._finnhub is not None:
            results: List[Dict] = []
            consecutive_rate_limit = 0
            for sym in tickers:
                try:
                    snap = self._finnhub.get_stock_snapshot(sym)

                    if snap is None:
                        results.append({"ticker": sym, "error": "No data from Finnhub"})
                        print(f"   ↳ {sym:<6} no-data")
                        continue

                    price_val = snap.get("current_price", 0)
                    mc_val = snap.get("market_cap", 0)
                    hi52 = snap.get("52w_high") or snap.get("year_high")

                    print(
                        f"   ↳ {sym:<6} ${price_val:>8.2f} | Cap {mc_val/1e9:>6.1f}B | 52wH {hi52 if hi52 else 'n/a'}"
                    )
                except RateLimitError as rl_err:
                    consecutive_rate_limit += 1
                    # After 3 consecutive 429s, disable Finnhub for rest of run
                    if consecutive_rate_limit >= 3:
                        print("🚦 Finnhub rate-limit hit – disabling Finnhub for this session and falling back to Yahoo.")
                        self._finnhub = None
                        # Recurse into same function which will now use Yahoo path
                        remaining = tickers[tickers.index(sym):]
                        return self._bulk_fetch_basic_info(remaining)
                    results.append({"ticker": sym, "error": str(rl_err)})
                    continue
                else:
                    consecutive_rate_limit = 0

                mc = snap.get("market_cap", 0) or 0
                vol = snap.get("volume", 0) or 0

                raw_ex = (snap.get("exchange", "") or "").upper()
                if raw_ex.startswith("NASDAQ") or raw_ex.startswith("NAS"):
                    ex = "NMS"
                elif raw_ex.startswith("NEW YORK") or raw_ex.startswith("NYSE") or raw_ex.startswith("NY "):
                    ex = "NYQ"
                elif "GLOBAL MARKET" in raw_ex:
                    ex = "NGM"
                elif "CAPITAL MARKET" in raw_ex:
                    ex = "NCM"
                else:
                    ex = raw_ex[:3] if raw_ex else "UNK"

                if not mc or not ex:
                    results.append({
                        "ticker": sym,
                        "error": f"Missing data (MC={mc}, Ex={ex})"
                    })
                    continue

                info_clean = {
                    "ticker": sym,
                    "market_cap": mc,
                    "volume": vol,
                    "exchange": ex,
                    "exchange_full": raw_ex,
                    "full_data": snap,
                    "_from_cache": False,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                results.append(info_clean)

            return results

        # ---------------- Yahoo fallback (original implementation) ----------------
        url = "https://query1.finance.yahoo.com/v7/finance/quote"

        # Re-use a Session with retry/back-off configured once
        if not hasattr(self, "_rq_session"):
            s = requests.Session()
            s.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
                "Accept": "application/json, text/javascript, */*; q=0.01",
            })
            retry = Retry(total=3, backoff_factor=5, status_forcelist=[429, 500, 502, 503, 504])
            s.mount("https://", HTTPAdapter(max_retries=retry))
            self._rq_session = s

        aggregate_results = []
        for sub_batch in self._chunked(tickers, 50):  # Yahoo behaves better ≤50 symbols
            time.sleep(1)  # stay well under Yahoo rate-limit
            resp = self._rq_session.get(url, params={"symbols": ",".join(sub_batch)}, timeout=10)
            if resp.status_code == 429:
                print("🚦 Yahoo quote API 429 even after throttling – aborting.")
                raise RateLimitError("Yahoo quote API 429 rate-limit")
            if resp.status_code != 200:
                aggregate_results.extend([{"ticker": t, "error": f"HTTP {resp.status_code} on v7 quote"} for t in sub_batch])
                continue

            part = resp.json()
            aggregate_results.append(part)

        # merge quote items from all parts
        quote_items = []
        for part in aggregate_results:
            if isinstance(part, dict):
                quote_items.extend(part.get("quoteResponse", {}).get("result", []))

        lookup = {item.get("symbol"): item for item in quote_items}
        # existing logic below will use lookup
        # if no quote_items collected due to errors
        if not quote_items:
            return [{"ticker": t, "error": "No quote data"} for t in tickers]

        results: List[Dict] = []
        for sym in tickers:
            itm = lookup.get(sym)
            if not itm:
                results.append({"ticker": sym, "error": "No quote data"})
                continue

            mc = itm.get("marketCap", 0) or itm.get("enterpriseValue", 0)
            vol = (
                itm.get("regularMarketVolume", 0)
                or itm.get("averageDailyVolume10Day", 0)
                or itm.get("averageDailyVolume3Month", 0)
            ) or 0
            ex = (
                itm.get("exchange")
                or (itm.get("fullExchangeName", "")[:3].upper())
            )

            if not mc or not vol or not ex:
                results.append({
                    "ticker": sym,
                    "error": f"Missing data (MC={mc}, Vol={vol}, Ex={ex})"
                })
                continue

            info_clean = {
                "ticker": sym,
                "market_cap": mc,
                "volume": vol,
                "exchange": ex,
                "full_data": itm,
                "_from_cache": False,
                "timestamp": datetime.utcnow().isoformat(),
            }
            results.append(info_clean)

        return results

    def _build_master_list_bulk(self, all_tickers: List[str],
                                 min_market_cap: float,
                                 min_volume: int,
                                 exchanges: List[str],
                                 target_size: int) -> Dict:
        """New high-throughput bulk implementation for master list creation."""
        BATCH_SIZE = 150  # Safe Yahoo hard limit is 1500, keep small for reliability
        total_batches = math.ceil(len(all_tickers) / BATCH_SIZE)
        filtered_stocks: List[Dict] = []
        processed = 0
        processed_symbols = set()
        errors = 0
        api_calls = 0
        cached_hits = 0  # Not used in bulk yet
        start_time = time.time()
        processed_skip = set()

        for batch_idx, batch in enumerate(self._chunked(all_tickers, BATCH_SIZE), 1):
            print(f"\n🌐 [Bulk {batch_idx}/{total_batches}] Fetching {len(batch)} tickers…", flush=True)
            api_calls += 1
            try:
                batch_results = self._bulk_fetch_basic_info(batch)
            except RateLimitError as rl_err:
                # bubble up to terminate entire master-list build
                print(f"🚨 Rate-limit encountered ({rl_err}). Aborting master-list build.")
                raise
            batch_errors = 0
            batch_qualified = 0

            for res in batch_results:
                processed += 1
                if res.get("ticker"):
                    processed_symbols.add(res["ticker"])
                if 'error' in res:
                    errors += 1
                    batch_errors += 1
                    # Show minimal error output – highlight crumb errors distinctly
                    if ('Invalid Crumb' in res['error']) and (batch_errors <= 3):
                        print(f"⚠️  {res['ticker']}: Crumb error")
                    elif batch_errors <= 2:
                        print(f"⚠️  {res['ticker']}: {res['error']}")
                    continue

                # Add quality score & filter
                res['quality_score'] = self._calculate_basic_quality_score(res)
                if self._passes_master_list_filters(res, min_market_cap, min_volume, exchanges):
                    filtered_stocks.append(res)
                    batch_qualified += 1

            # End of batch – print concise summary
            sample = ", ".join([s['ticker'] for s in filtered_stocks[-5:]]) if filtered_stocks else ""

            # ETA calculation
            elapsed_total = time.time() - start_time
            avg_per_batch = elapsed_total / batch_idx if batch_idx else 0
            remaining_batches = total_batches - batch_idx
            eta_sec = int(avg_per_batch * remaining_batches)
            eta_min, eta_rem = divmod(eta_sec, 60)

            print(
                f"   📋 Batch {batch_idx}/{total_batches} done | qualified {batch_qualified}/{len(batch_results)} "
                f"| cum {len(filtered_stocks)} | errors {batch_errors} | ETA {eta_min}m {eta_rem}s"
            )
            if batch_qualified and sample:
                print(f"      🏆 Latest qualifiers: {sample}")
            # polite pause to stay well under 60 req/min (use 4 s)
            time.sleep(4.0)

            # ---------------------- checkpoint ----------------------
            try:
                checkpoint = {
                    "created": datetime.utcnow().isoformat(),
                    "filter_criteria": {
                        "min_market_cap": min_market_cap,
                        "min_volume": min_volume,
                        "exchanges": exchanges,
                        "target_size": target_size,
                    },
                    "stats": {
                        "partial": True,
                        "processed": processed,
                        "qualified": len(filtered_stocks),
                        "batch": batch_idx,
                    },
                    "stocks": filtered_stocks,
                    "processed_symbols": list(processed_symbols),
                }
                with open(MASTER_LIST_FILE, "w") as f:
                    json.dump(checkpoint, f, indent=2)
            except Exception:
                pass  # never fail run on checkpoint error

        elapsed = time.time() - start_time
        if not filtered_stocks:
            print("❌ No qualified stocks found in bulk pass.")
            return {}

        print(f"\n📊 Bulk pass complete – processed {processed:,} tickers | qualified {len(filtered_stocks):,}")

        # Rank and trim
        ranked_stocks = self._rank_stocks_for_master_list(filtered_stocks)
        master_list_stocks = ranked_stocks[:target_size]

        master_list_data = {
            'created': datetime.now().isoformat(),
            'filter_criteria': {
                'min_market_cap': min_market_cap,
                'min_volume': min_volume,
                'exchanges': exchanges,
                'target_size': target_size
            },
            'stats': {
                'total_analyzed': processed,
                'total_passed_filters': len(filtered_stocks),
                'total_in_master_list': len(master_list_stocks),
                'cache_hits': cached_hits,
                'api_calls': api_calls,
                'processing_time_minutes': elapsed / 60,
                'errors': errors,
            },
            'stocks': master_list_stocks
        }

        # Save
        with open(MASTER_LIST_FILE, 'w') as f:
            json.dump(master_list_data, f, indent=2)

        print(f"\n✅ MASTER LIST CREATED (bulk mode)")
        print(f"   • Final size: {len(master_list_stocks):,} stocks")
        print(f"   • Saved to: {MASTER_LIST_FILE}")
        print(f"   • Processed: {processed:,} tickers in {elapsed/60:.1f} min")
        return master_list_data
    
    def get_screening_list(self, size: int = 500, 
                          max_age_hours: int = 24) -> Optional[List[str]]:
        """
        Get Tier 2: Screening List of top N candidates from master list.
        """
        screening_file = Path(SCREENING_LISTS_DIR) / f"top_{size}.json"
        
        # Check if existing screening list is fresh
        if screening_file.exists():
            try:
                with open(screening_file, 'r') as f:
                    data = json.load(f)
                
                created = datetime.fromisoformat(data.get('created', '2000-01-01'))
                age_hours = (datetime.now() - created).total_seconds() / 3600
                
                if age_hours < max_age_hours:
                    print(f"📋 Using cached screening list (age: {age_hours:.1f}h)")
                    return data.get('tickers', [])
            except Exception:
                pass
        
        # Need to build new screening list
        return self._build_screening_list(size)
    
    def _build_screening_list(self, size: int) -> List[str]:
        """Build a new screening list from the master list."""
        print(f"🎯 BUILDING TIER 2: SCREENING LIST (TOP {size})")
        print("=" * 50)
        
        # Load master list
        if not Path(MASTER_LIST_FILE).exists():
            print("❌ Master list not found. Run --build-master-list first.")
            return []
        
        print(f"   📂 Loading master list from {MASTER_LIST_FILE}")
        try:
            with open(MASTER_LIST_FILE, 'r') as f:
                master_data = json.load(f)
            print(f"   ✅ Master list loaded successfully")
        except Exception as e:
            print(f"❌ Error loading master list: {e}")
            return []
        
        master_stocks = master_data.get('stocks', [])
        print(f"   📊 Master list contains {len(master_stocks):,} stocks")
        
        if len(master_stocks) == 0:
            print("❌ Master list is empty. Rebuild with --build-master-list")
            return []
        
        # Show master list statistics
        if master_stocks:
            quality_scores = [stock.get('quality_score', 0) for stock in master_stocks]
            market_caps = [stock.get('market_cap', 0) for stock in master_stocks]
            print(f"   📈 Quality scores range: {min(quality_scores):.1f} - {max(quality_scores):.1f}")
            print(f"   💰 Market caps range: ${min(market_caps)/1e9:.1f}B - ${max(market_caps)/1e9:.1f}B")
        
        # Apply screening criteria (dip detection, momentum, etc.)
        print(f"   🔍 Applying screening criteria to select top {size} candidates...")
        print(f"      📊 Sorting by quality score (market cap + volume + exchange preference)")
        screened_stocks = self._apply_screening_criteria(master_stocks, size)
        
        if screened_stocks:
            print(f"   ✅ Selected top {len(screened_stocks)} stocks:")
            # Show sample of selected stocks
            sample_size = min(10, len(screened_stocks))
            print(f"      🏆 Top {sample_size}: {', '.join(screened_stocks[:sample_size])}")
            if len(screened_stocks) > sample_size:
                print(f"      ... and {len(screened_stocks) - sample_size} more")
        
        # Save screening list
        screening_file = Path(SCREENING_LISTS_DIR) / f"top_{size}.json"
        print(f"   💾 Saving screening list to {screening_file}")
        
        screening_data = {
            'created': datetime.now().isoformat(),
            'size': size,
            'master_list_size': len(master_stocks),
            'screening_criteria': 'Quality score ranking (market cap + volume + exchange)',
            'tickers': screened_stocks
        }
        
        with open(screening_file, 'w') as f:
            json.dump(screening_data, f, indent=2)
        
        print(f"   ✅ Screening list created successfully!")
        print(f"      📁 File: {screening_file}")
        print(f"      📊 Size: {len(screened_stocks)} tickers")
        print(f"      ⏰ Valid for: {24} hours")
        
        return screened_stocks
    
    def _apply_screening_criteria(self, master_stocks: List[Dict], size: int) -> List[str]:
        """Apply screening criteria to select top candidates from master list."""
        # For now, use a simple approach based on quality score and market cap
        # In the future, this could include:
        # - Dip detection (price vs 52-week high)
        # - Technical indicators (RSI, moving averages)
        # - Fundamental screening (P/E ratios, debt levels)
        # - Momentum indicators
        
        # Sort by quality score and take top N
        sorted_stocks = sorted(master_stocks, 
                             key=lambda x: x.get('quality_score', 0), 
                             reverse=True)
        
        top_stocks = sorted_stocks[:size]
        return [stock['ticker'] for stock in top_stocks]
    
    def get_master_list_tickers(self) -> List[str]:
        """Get list of all tickers in the master list."""
        if not Path(MASTER_LIST_FILE).exists():
            return []
        
        try:
            with open(MASTER_LIST_FILE, 'r') as f:
                data = json.load(f)
            return [stock['ticker'] for stock in data.get('stocks', [])]
        except Exception:
            return []


if __name__ == "__main__":
    
    manager = MasterListManager()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python master_list.py build     # Build master list")
        print("  python master_list.py screen N  # Create screening list of size N")
        print("  python master_list.py status    # Show status")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "build":
        manager.build_master_list()
    
    elif command == "screen":
        size = int(sys.argv[2]) if len(sys.argv) > 2 else 500
        tickers = manager.get_screening_list(size)
        print(f"Screening list: {tickers[:10]}..." if len(tickers) > 10 else f"Screening list: {tickers}")
    
    elif command == "status":
        stats = manager.get_master_list_stats()
        if stats:
            print(f"Master List Status:")
            print(f"  Size: {stats['total_stocks']:,} stocks")
            print(f"  Age: {stats['age_days']} days")
            print(f"  Fresh: {'✅' if stats['fresh'] else '❌'}")
        else:
            print("❌ No master list found")
    
    else:
        print(f"Unknown command: {command}") 