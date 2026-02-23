"""
Delphi - Day 4: Oracle Logic
Combines live Polymarket prices + per-candidate news sentiment to generate signals.

Signal rules (thresholds set in markets/[config].py):
  BUY YES  — sentiment bullish AND price < price_low_cutoff
              → candidate underpriced relative to social sentiment
  BUY NO   — sentiment bearish AND price > price_high_cutoff
              → candidate overpriced relative to social sentiment
  HOLD     — all other conditions
              → no clear divergence detected

Output:
  - Per-candidate signal table printed to terminal
  - Every run logged to data/[prefix]_predictions.csv
  - Prediction history shown for last 5 runs
"""

import csv
import os
import importlib.util
from datetime import datetime

from active_market import MARKET_CONFIG

# ── Import Day1 and Day3 pipelines ──────────────────────────────────────────────

def _import_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_base = os.path.dirname(os.path.abspath(__file__))
_day1 = _import_file("day1", os.path.join(_base, "Day1 Fetch Polymarket.py"))
_day3 = _import_file("day3", os.path.join(_base, "Day3 Sentiment Engine.py"))

fetch_market_by_slug           = _day1.fetch_market_by_slug
get_candidates                 = _day1.get_candidates
fetch_all_posts                  = _day3.fetch_all_posts
is_relevant                      = _day3.is_relevant
compute_all_candidates_sentiment = _day3.compute_all_candidates_sentiment


# ── Config ───────────────────────────────────────────────────────────────────────

ORACLE_CONFIG     = MARKET_CONFIG["oracle"]
SENTIMENT_CONFIG  = MARKET_CONFIG["sentiment"]

PRICE_LOW_CUTOFF  = ORACLE_CONFIG["price_low_cutoff"]
PRICE_HIGH_CUTOFF = ORACLE_CONFIG["price_high_cutoff"]
BULLISH_THRESHOLD = SENTIMENT_CONFIG["bullish_threshold"]
BEARISH_THRESHOLD = SENTIMENT_CONFIG["bearish_threshold"]
MIN_SIGNAL_POSTS  = MARKET_CONFIG.get("min_signal_posts", 3)

CSV_PATH = os.path.join("data", f"{MARKET_CONFIG['data_prefix']}_predictions.csv")


# ── Oracle Signal Logic ──────────────────────────────────────────────────────────

def generate_signal(sentiment_score: float | None, price: float, posts_analyzed: int = 0) -> dict:
    """
    Generate BUY YES / BUY NO / HOLD signal for one candidate.

    sentiment_score:  normalized 0-1 (None = no news data for this candidate)
    price:            current market probability as 0-1 (e.g. 0.63 = 63%)
    posts_analyzed:   number of qualifying posts used to compute sentiment
    """
    if sentiment_score is None:
        return {
            "signal":     "HOLD",
            "action":     "—",
            "confidence": 0.0,
            "reasoning":  "No news data found for this candidate.",
        }

    if posts_analyzed < MIN_SIGNAL_POSTS:
        return {
            "signal":     "HOLD",
            "action":     "⚠️  HOLD",
            "confidence": 0.0,
            "reasoning":  (
                f"Insufficient data: only {posts_analyzed} post(s) found "
                f"(minimum {MIN_SIGNAL_POSTS} required to fire a signal)."
            ),
        }

    # BUY YES: news is bullish but price hasn't caught up
    if sentiment_score >= BULLISH_THRESHOLD and price < PRICE_LOW_CUTOFF:
        confidence = round(
            (sentiment_score - BULLISH_THRESHOLD) * 2 + (PRICE_LOW_CUTOFF - price) * 2, 3
        )
        return {
            "signal":     "BUY YES",
            "action":     "📈 BUY YES",
            "confidence": min(confidence, 1.0),
            "reasoning":  (
                f"Sentiment bullish ({sentiment_score:.3f} >= {BULLISH_THRESHOLD}) "
                f"but price low ({price*100:.1f}% < {PRICE_LOW_CUTOFF*100:.0f}%). Underpriced."
            ),
        }

    # BUY NO: news is bearish but price is still high
    if sentiment_score <= BEARISH_THRESHOLD and price > PRICE_HIGH_CUTOFF:
        confidence = round(
            (BEARISH_THRESHOLD - sentiment_score) * 2 + (price - PRICE_HIGH_CUTOFF) * 2, 3
        )
        return {
            "signal":     "BUY NO",
            "action":     "📉 BUY NO",
            "confidence": min(confidence, 1.0),
            "reasoning":  (
                f"Sentiment bearish ({sentiment_score:.3f} <= {BEARISH_THRESHOLD}) "
                f"but price high ({price*100:.1f}% > {PRICE_HIGH_CUTOFF*100:.0f}%). Overpriced."
            ),
        }

    # HOLD
    neutral_range   = BULLISH_THRESHOLD - BEARISH_THRESHOLD
    margin          = min(BULLISH_THRESHOLD - sentiment_score, sentiment_score - BEARISH_THRESHOLD)
    hold_confidence = round(max(0.0, min(margin / (neutral_range / 2), 1.0)), 3)

    return {
        "signal":     "HOLD",
        "action":     "➡️  HOLD",
        "confidence": hold_confidence,
        "reasoning":  (
            f"No divergence. Sentiment: {sentiment_score:.3f} | "
            f"Price: {price*100:.1f}%"
        ),
    }


# ── CSV Logging ──────────────────────────────────────────────────────────────────

def log_predictions(timestamp: str, candidate_signals: list) -> None:
    """Append one row per candidate to the predictions CSV."""
    os.makedirs("data", exist_ok=True)
    file_exists = os.path.isfile(CSV_PATH)

    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "timestamp", "market", "candidate", "market_price_pct",
            "sentiment_score", "sentiment_label",
            "signal", "confidence", "reasoning"
        ])
        if not file_exists:
            writer.writeheader()

        for row in candidate_signals:
            writer.writerow({
                "timestamp":        timestamp,
                "market":           MARKET_CONFIG["name"],
                "candidate":        row["name"],
                "market_price_pct": f"{row['price']*100:.2f}",
                "sentiment_score":  row["sentiment_score"] if row["sentiment_score"] is not None else "",
                "sentiment_label":  row["sentiment_label"],
                "signal":           row["signal"]["signal"],
                "confidence":       row["signal"]["confidence"],
                "reasoning":        row["signal"]["reasoning"],
            })

    print(f"  💾 Logged to {CSV_PATH}")


def load_past_predictions() -> list:
    if not os.path.isfile(CSV_PATH):
        return []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ── Display ───────────────────────────────────────────────────────────────────────

def display_signals(candidate_signals: list, timestamp: str) -> None:
    print("\n" + "=" * 85)
    print("🔮 DELPHI - SIGNALS")
    print("=" * 85)
    print(f"🎯 Market : {MARKET_CONFIG['name']}")
    print(f"🕐 Time   : {timestamp}")
    print(f"  Price thresholds : BUY YES if price < {PRICE_LOW_CUTOFF*100:.0f}%  |  BUY NO if price > {PRICE_HIGH_CUTOFF*100:.0f}%")
    print(f"  Sentiment thresholds : bullish >= {BULLISH_THRESHOLD}  |  bearish <= {BEARISH_THRESHOLD}")
    print("=" * 85)
    print("{:<20} {:>7}  {:>7}  {:>6}  {:>7}  {:>6}  {}".format(
        "Candidate", "Price", "Senti.", "Posts", "Label", "Conf.", "Signal"))
    print("-" * 90)

    for row in candidate_signals:
        price   = row["price"]
        score   = row["sentiment_score"]
        label   = row["sentiment_label"]
        sig     = row["signal"]
        posts   = row.get("posts_analyzed", 0)
        score_str = f"{score:.3f}" if score is not None else "  N/A"
        print("{:<20} {:>6.1f}%  {:>7}  {:>6}  {:>7}  {:>6.3f}  {}".format(
            row["name"],
            price * 100,
            score_str,
            posts,
            label,
            sig["confidence"],
            sig["action"],
        ))

    # Highlight any non-HOLD signals with reasoning
    actionable = [r for r in candidate_signals if r["signal"]["signal"] != "HOLD"]
    if actionable:
        print("\n" + "-" * 85)
        print("  ACTIONABLE SIGNALS:")
        for row in actionable:
            print(f"\n  {row['signal']['action']}  →  {row['name']}")
            print(f"  Buy YES: ${row['buy_yes']:.3f}  |  Buy NO: ${row['buy_no']:.3f}")
            print(f"  {row['signal']['reasoning']}")
    else:
        print("\n  No actionable signals this run — all HOLD.")

    print("=" * 85)


def display_history(past_predictions: list) -> None:
    if len(past_predictions) < 2:
        return
    print("\n" + "-" * 85)
    print("  PREDICTION HISTORY (last 5 runs):")
    print("-" * 85)
    recent = past_predictions[-5:]
    for p in recent:
        sig  = p.get("signal", "?")
        ts   = p.get("timestamp", "?")
        cand = p.get("candidate", "?")
        prc  = p.get("market_price_pct", "?")
        icon = "📈" if sig == "BUY YES" else "📉" if sig == "BUY NO" else "➡️ "
        print(f"  {icon} {sig:8}  |  {cand:20}  |  {ts}  |  Price: {prc}%")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "🔮" * 35)
    print("        DELPHI - ORACLE ENGINE")
    print("              (Sentiment × Market = Signal · per-candidate)")
    print("🔮" * 35 + "\n")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Step 1: Fetch Polymarket prices
    print("📡 Fetching Polymarket data...")
    event_data = fetch_market_by_slug(MARKET_CONFIG["slug"])
    if not event_data:
        print("❌ Could not fetch Polymarket data. Aborting.")
        return

    market_candidates = get_candidates(event_data, min_probability=0.0)
    # Build lookup: name → {price, buy_yes, buy_no}
    price_lookup = {
        c["name"]: {
            "price":   c["probability"] / 100,
            "buy_yes": c.get("buy_yes", 0),
            "buy_no":  c.get("buy_no", 0),
        }
        for c in market_candidates
    }
    print(f"  ✅ {len(market_candidates)} candidates fetched\n")

    # Step 2: Fetch news + compute per-candidate sentiment
    print("📡 Fetching news sentiment...")
    all_posts = fetch_all_posts()   # Google News RSS via Day3

    relevant = [p for p in all_posts if is_relevant(p)]
    print(f"  ✅ {len(relevant)} relevant articles found\n")

    sentiment_results = compute_all_candidates_sentiment(relevant)

    # Step 3: Generate signals for each candidate that has market data
    candidate_signals = []
    for candidate, sent_result in sentiment_results.items():
        if candidate not in price_lookup:
            continue   # not in this market's active candidates
        prices = price_lookup[candidate]
        score  = sent_result["normalized_score"] if sent_result else None
        label  = sent_result["label"] if sent_result else "no_data"
        posts  = sent_result["posts_analyzed"] if sent_result else 0
        signal = generate_signal(score, prices["price"], posts_analyzed=posts)

        candidate_signals.append({
            "name":            candidate,
            "price":           prices["price"],
            "buy_yes":         prices["buy_yes"],
            "buy_no":          prices["buy_no"],
            "sentiment_score": score,
            "sentiment_label": label,
            "posts_analyzed":  posts,
            "signal":          signal,
        })

    # Sort by price descending (frontrunner first)
    candidate_signals.sort(key=lambda x: x["price"], reverse=True)

    # Step 4: Display
    display_signals(candidate_signals, timestamp)

    # Step 5: Show history
    past = load_past_predictions()
    display_history(past)

    # Step 6: Log
    log_predictions(timestamp, candidate_signals)

    actionable_count = sum(1 for r in candidate_signals if r["signal"]["signal"] != "HOLD")
    print(f"\n✅ Delphi complete!  {actionable_count} actionable signal(s) this run.\n")


if __name__ == "__main__":
    main()
