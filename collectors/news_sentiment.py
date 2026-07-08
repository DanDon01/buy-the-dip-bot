"""
News sentiment collector.

Fetches recent company headlines from Finnhub (free tier: /company-news) and
scores them with a built-in financial-news lexicon - no heavyweight ML
dependency, deterministic, and fully offline-testable.

The aggregate sentiment (-1..+1) is cached per ticker in
cache/news_sentiment.json (TTL 12h) so the scoring loop and API can consume
it without extra API calls.

CLI:  python cli.py --news --ticker AAPL
API:  GET /api/stock/<ticker>/news
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional

CACHE_FILE = os.path.join("cache", "news_sentiment.json")
CACHE_TTL_HOURS = 12

# Compact financial-news lexicon. Deliberately biased toward words common in
# headlines; weights in [-1, 1].
POSITIVE_WORDS = {
    "beat": 1.0, "beats": 1.0, "surge": 0.9, "surges": 0.9, "soar": 0.9,
    "soars": 0.9, "rally": 0.8, "rallies": 0.8, "jump": 0.7, "jumps": 0.7,
    "gain": 0.6, "gains": 0.6, "rise": 0.5, "rises": 0.5, "record": 0.6,
    "growth": 0.6, "profit": 0.6, "profits": 0.6, "strong": 0.6,
    "upgrade": 0.9, "upgrades": 0.9, "upgraded": 0.9, "outperform": 0.8,
    "buy": 0.5, "bullish": 0.8, "boost": 0.6, "boosts": 0.6,
    "exceed": 0.8, "exceeds": 0.8, "expand": 0.5, "expands": 0.5,
    "partnership": 0.5, "dividend": 0.4, "buyback": 0.6, "breakthrough": 0.8,
    "approval": 0.7, "approved": 0.7, "wins": 0.7, "win": 0.6,
    "raises": 0.6, "raised": 0.6, "recovery": 0.5, "rebound": 0.6,
    "innovative": 0.4, "launch": 0.3, "launches": 0.3, "positive": 0.6,
}

NEGATIVE_WORDS = {
    "miss": -1.0, "misses": -1.0, "missed": -1.0, "plunge": -0.9,
    "plunges": -0.9, "crash": -1.0, "crashes": -1.0, "tumble": -0.8,
    "tumbles": -0.8, "sink": -0.7, "sinks": -0.7, "drop": -0.6,
    "drops": -0.6, "fall": -0.5, "falls": -0.5, "decline": -0.5,
    "declines": -0.5, "loss": -0.6, "losses": -0.6, "weak": -0.6,
    "downgrade": -0.9, "downgrades": -0.9, "downgraded": -0.9,
    "underperform": -0.8, "sell": -0.5, "bearish": -0.8, "cut": -0.5,
    "cuts": -0.5, "layoff": -0.7, "layoffs": -0.7, "lawsuit": -0.7,
    "investigation": -0.7, "probe": -0.6, "fraud": -1.0, "bankruptcy": -1.0,
    "bankrupt": -1.0, "recall": -0.7, "warning": -0.6, "warns": -0.7,
    "fears": -0.6, "fear": -0.5, "risk": -0.4, "risks": -0.4,
    "slump": -0.8, "slumps": -0.8, "halt": -0.6, "halts": -0.6,
    "delisting": -0.9, "default": -0.9, "negative": -0.6, "lowers": -0.6,
}

_WORD_RE = re.compile(r"[a-z']+")


def score_headline(text: str) -> float:
    """Score a single headline in [-1, 1] using the lexicon."""
    if not text:
        return 0.0
    words = _WORD_RE.findall(text.lower())
    if not words:
        return 0.0
    total = 0.0
    hits = 0
    for i, w in enumerate(words):
        weight = POSITIVE_WORDS.get(w) or NEGATIVE_WORDS.get(w)
        if weight is None:
            continue
        # Simple negation handling: "not", "no", "fails to" flip the sign
        if i > 0 and words[i - 1] in {"not", "no", "fails", "failed", "without"}:
            weight = -weight
        total += weight
        hits += 1
    if hits == 0:
        return 0.0
    return max(-1.0, min(1.0, total / max(hits, 2)))


def aggregate_sentiment(headlines: List[str]) -> Dict:
    """Aggregate headline scores into an overall sentiment summary."""
    scored = [(h, score_headline(h)) for h in headlines if h]
    if not scored:
        return {"sentiment_score": 0.0, "article_count": 0,
                "positive": 0, "negative": 0, "neutral": 0, "label": "no_data"}

    values = [s for _, s in scored]
    avg = sum(values) / len(values)
    positive = sum(1 for v in values if v > 0.1)
    negative = sum(1 for v in values if v < -0.1)
    neutral = len(values) - positive - negative

    if avg >= 0.25:
        label = "very_positive"
    elif avg >= 0.08:
        label = "positive"
    elif avg <= -0.25:
        label = "very_negative"
    elif avg <= -0.08:
        label = "negative"
    else:
        label = "neutral"

    return {
        "sentiment_score": round(avg, 3),
        "article_count": len(values),
        "positive": positive,
        "negative": negative,
        "neutral": neutral,
        "label": label,
    }


class NewsSentimentCollector:
    """Fetches Finnhub company news and produces a sentiment summary."""

    def __init__(self, finnhub_collector=None):
        self._finnhub = finnhub_collector
        if self._finnhub is None:
            try:
                from collectors.finnhub_collector import FinnhubCollector
                self._finnhub = FinnhubCollector()
            except Exception:
                self._finnhub = None   # key missing - cache-only mode

    def get_sentiment(self, ticker: str, days: int = 7,
                      use_cache: bool = True) -> Dict:
        """Sentiment summary for a ticker's recent news."""
        ticker = ticker.upper()
        cache = _load_cache()
        if use_cache and ticker in cache:
            entry = cache[ticker]
            try:
                if datetime.now() - datetime.fromisoformat(entry["fetched"]) \
                        <= timedelta(hours=CACHE_TTL_HOURS):
                    return entry["data"]
            except (KeyError, ValueError):
                pass

        articles = self._fetch_news(ticker, days)
        if articles is None:
            # No API access - return cached (stale) data or an empty result
            if ticker in cache:
                return cache[ticker]["data"]
            return {**aggregate_sentiment([]), "ticker": ticker, "headlines": []}

        headlines = [a.get("headline", "") for a in articles]
        summary = aggregate_sentiment(headlines)
        summary["ticker"] = ticker
        summary["headlines"] = [
            {
                "headline": a.get("headline", ""),
                "source": a.get("source", ""),
                "url": a.get("url", ""),
                "datetime": datetime.fromtimestamp(a["datetime"]).isoformat()
                if a.get("datetime") else None,
                "sentiment": round(score_headline(a.get("headline", "")), 3),
            }
            for a in articles[:10]
        ]

        cache[ticker] = {"fetched": datetime.now().isoformat(), "data": summary}
        _save_cache(cache)
        return summary

    def _fetch_news(self, ticker: str, days: int) -> Optional[List[Dict]]:
        """Fetch raw company news from Finnhub. None => API unavailable."""
        if self._finnhub is None:
            return None
        try:
            client = self._finnhub._client
            self._finnhub._throttle()
            end = datetime.now().date()
            start = end - timedelta(days=days)
            articles = client.company_news(ticker, _from=str(start), to=str(end))
            return articles if isinstance(articles, list) else []
        except Exception as e:
            print(f"⚠️  Finnhub news fetch failed for {ticker}: {e}")
            return None


def sentiment_adjustment_for(ticker: str, max_points: float = 2.0) -> float:
    """Risk-modifier adjustment (± max_points) from *cached* sentiment only.

    Never triggers an API call - safe to use inside the scoring loop.
    """
    cache = _load_cache()
    entry = cache.get(ticker.upper())
    if not entry:
        return 0.0
    try:
        if datetime.now() - datetime.fromisoformat(entry["fetched"]) \
                > timedelta(hours=CACHE_TTL_HOURS * 4):
            return 0.0   # too stale to act on
    except (KeyError, ValueError):
        return 0.0
    score = entry.get("data", {}).get("sentiment_score", 0) or 0
    return max(-max_points, min(max_points, score * max_points * 2))


def _load_cache() -> Dict:
    try:
        with open(CACHE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_cache(cache: Dict):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)
