"""
Delphi Oracle - Day 3: Sentiment Analysis Engine
Source: Reddit posts fetched live via Day2 pipeline
Method: VADER (baseline) with LLM-ready architecture

Scoring (per candidate):
  - All Reddit posts are fetched once using the broad keyword list
  - Each candidate's posts are filtered by that candidate's specific keywords
  - Posts scored -1 to +1 by VADER, weighted by upvotes
  - Aggregate score mapped to: bearish / neutral / bullish
  - Results logged to data/[prefix]_sentiment.csv

LLM hook:
  - analyze_post_sentiment() is the single function to upgrade later
  - Replace or wrap it to add Claude/GPT analysis without touching anything else
"""

import csv
import os
from datetime import datetime, timezone
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

import importlib.util
from active_market import MARKET_CONFIG

def _import_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_base = os.path.dirname(os.path.abspath(__file__))
_day2 = _import_file("day2", os.path.join(_base, "Day2 Fetch Reddit.py"))

fetch_subreddit_posts = _day2.fetch_subreddit_posts
is_relevant           = _day2.is_relevant
SUBREDDITS_NEW        = _day2.SUBREDDITS_NEW
SUBREDDITS_HOT        = _day2.SUBREDDITS_HOT


# ── Config ───────────────────────────────────────────────────────────────────────

SENTIMENT_CONFIG  = MARKET_CONFIG["sentiment"]
BULLISH_THRESHOLD = SENTIMENT_CONFIG["bullish_threshold"]
BEARISH_THRESHOLD = SENTIMENT_CONFIG["bearish_threshold"]
CANDIDATE_KEYWORDS = MARKET_CONFIG.get("candidates", {})  # {company: [keywords]}

CSV_PATH = os.path.join("data", f"{MARKET_CONFIG['data_prefix']}_sentiment.csv")

MIN_SCORE_TO_INCLUDE = 0   # ignore posts with 0 or negative upvotes


# ── Sentiment Scoring ────────────────────────────────────────────────────────────

_analyzer = SentimentIntensityAnalyzer()


def analyze_post_sentiment(post: dict) -> dict:
    """
    Score a single Reddit post for sentiment.

    LLM upgrade point: replace or wrap this function to add Claude/GPT analysis.

    Returns:
        dict with keys: compound, positive, negative, neutral, method
    """
    text = (post.get("title", "") + " " + post.get("selftext", "")).strip()
    scores = _analyzer.polarity_scores(text)
    return {
        "compound": scores["compound"],
        "positive": scores["pos"],
        "negative": scores["neg"],
        "neutral":  scores["neu"],
        "method":   "vader",
    }


def normalize(compound: float) -> float:
    """Convert VADER compound (-1 to +1) to 0-1 scale."""
    return (compound + 1) / 2


def score_to_label(normalized_score: float) -> str:
    """Map a 0-1 normalized score to a human-readable label."""
    if normalized_score >= BULLISH_THRESHOLD:
        return "bullish"
    elif normalized_score <= BEARISH_THRESHOLD:
        return "bearish"
    else:
        return "neutral"


def post_mentions_candidate(post: dict, keywords: list) -> bool:
    """Return True if the post title or body contains any of the candidate's keywords."""
    text = (post.get("title", "") + " " + post.get("selftext", "")).lower()
    return any(kw.lower() in text for kw in keywords)


# ── Per-Candidate Aggregation ────────────────────────────────────────────────────

def compute_candidate_sentiment(posts: list, keywords: list) -> dict | None:
    """
    Compute upvote-weighted sentiment for a single candidate using its keywords.

    Returns None if no qualifying posts found.
    """
    scored_posts = []
    total_weight = 0

    for post in posts:
        if not post_mentions_candidate(post, keywords):
            continue
        upvotes = post.get("score", 0)
        if upvotes <= MIN_SCORE_TO_INCLUDE:
            continue

        sentiment = analyze_post_sentiment(post)
        weight    = upvotes

        scored_posts.append({
            "title":      post.get("title", "")[:80],
            "subreddit":  post.get("subreddit_name_prefixed", ""),
            "upvotes":    upvotes,
            "comments":   post.get("num_comments", 0),
            "compound":   sentiment["compound"],
            "normalized": normalize(sentiment["compound"]),
            "weight":     weight,
        })
        total_weight += weight

    if not scored_posts:
        return None

    weighted_sum      = sum(p["compound"] * p["weight"] for p in scored_posts)
    weighted_compound = weighted_sum / total_weight if total_weight > 0 else 0.0
    normalized_score  = normalize(weighted_compound)
    simple_avg        = sum(p["compound"] for p in scored_posts) / len(scored_posts)

    return {
        "posts_analyzed":    len(scored_posts),
        "total_weight":      total_weight,
        "weighted_compound": round(weighted_compound, 4),
        "simple_compound":   round(simple_avg, 4),
        "normalized_score":  round(normalized_score, 4),
        "label":             score_to_label(normalized_score),
        "posts":             scored_posts,
    }


def compute_all_candidates_sentiment(posts: list) -> dict:
    """
    Run per-candidate sentiment for every candidate in MARKET_CONFIG["candidates"].

    Returns {candidate_name: sentiment_result_or_None}
    """
    results = {}
    for candidate, keywords in CANDIDATE_KEYWORDS.items():
        results[candidate] = compute_candidate_sentiment(posts, keywords)
    return results


# ── CSV Logging ──────────────────────────────────────────────────────────────────

def log_to_csv(all_results: dict) -> None:
    """Append one row per candidate to the sentiment CSV."""
    os.makedirs("data", exist_ok=True)
    file_exists = os.path.isfile(CSV_PATH)
    timestamp   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "timestamp", "market", "candidate", "posts_analyzed", "total_weight",
            "weighted_compound", "simple_compound", "normalized_score", "label"
        ])
        if not file_exists:
            writer.writeheader()

        for candidate, result in all_results.items():
            if result is None:
                writer.writerow({
                    "timestamp": timestamp, "market": MARKET_CONFIG["name"],
                    "candidate": candidate, "posts_analyzed": 0, "total_weight": 0,
                    "weighted_compound": "", "simple_compound": "",
                    "normalized_score": "", "label": "no_data",
                })
            else:
                writer.writerow({
                    "timestamp":         timestamp,
                    "market":            MARKET_CONFIG["name"],
                    "candidate":         candidate,
                    "posts_analyzed":    result["posts_analyzed"],
                    "total_weight":      result["total_weight"],
                    "weighted_compound": result["weighted_compound"],
                    "simple_compound":   result["simple_compound"],
                    "normalized_score":  result["normalized_score"],
                    "label":             result["label"],
                })

    print(f"  💾 Logged to {CSV_PATH}")


# ── Display ───────────────────────────────────────────────────────────────────────

def display_results(all_results: dict) -> None:
    """Print per-candidate sentiment table."""
    print("\n" + "=" * 75)
    print("🔮 DELPHI ORACLE - SENTIMENT ANALYSIS (per candidate)")
    print("=" * 75)
    print(f"🎯 Market : {MARKET_CONFIG['name']}")
    print(f"🕐 Time   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Thresholds: bullish >= {BULLISH_THRESHOLD}  |  bearish <= {BEARISH_THRESHOLD}")
    print("=" * 75)
    print("{:<20} {:>7} {:>8} {:>8}  {}".format("Candidate", "Score", "Posts", "Upvotes", "Signal"))
    print("-" * 75)

    for candidate, result in all_results.items():
        if result is None:
            print("{:<20} {:>7}  {:>7}  {:>7}  {}".format(
                candidate, "N/A", "0", "0", "⚪ no data"))
            continue

        score = result["normalized_score"]
        label = result["label"]

        if label == "bullish":
            icon = "📈 BULLISH"
        elif label == "bearish":
            icon = "📉 BEARISH"
        else:
            icon = "➡️  NEUTRAL"

        print("{:<20} {:>7.4f}  {:>6}  {:>7,}  {}".format(
            candidate,
            score,
            result["posts_analyzed"],
            result["total_weight"],
            icon,
        ))

    # Top influential posts across all candidates
    all_posts = []
    for result in all_results.values():
        if result:
            all_posts.extend(result["posts"])

    if all_posts:
        top = sorted(all_posts, key=lambda p: p["upvotes"], reverse=True)[:5]
        print("\n" + "-" * 75)
        print("  TOP 5 MOST INFLUENTIAL POSTS:")
        print("-" * 75)
        for i, p in enumerate(top, 1):
            icon = "🟢" if p["compound"] >= 0.05 else "🔴" if p["compound"] <= -0.05 else "⚪"
            print(f"  {i}. {p['subreddit']}  |  ⬆ {p['upvotes']:,}  |  {icon} {p['compound']:+.3f}")
            print(f"     {p['title']}")

    print("=" * 75 + "\n")


# ── Main ──────────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "🔮" * 35)
    print("        DELPHI ORACLE - SENTIMENT ENGINE")
    print("              (VADER Baseline · per-candidate)")
    print("🔮" * 35 + "\n")

    # Step 1: Fetch Reddit posts (broad net via flat keywords)
    print("📡 Fetching Reddit posts...\n")
    all_posts = []
    for sub in SUBREDDITS_NEW:
        all_posts.extend(fetch_subreddit_posts(sub, sort="new"))
    for sub in SUBREDDITS_HOT:
        all_posts.extend(fetch_subreddit_posts(sub, sort="hot"))

    relevant_posts = [p for p in all_posts if is_relevant(p)]
    print(f"\n📥 {len(all_posts)} posts fetched  |  {len(relevant_posts)} relevant\n")

    if not relevant_posts:
        print("⚠️  No relevant posts found. Cannot compute sentiment.")
        return

    # Step 2: Score each candidate
    print("🧠 Analyzing per-candidate sentiment...\n")
    all_results = compute_all_candidates_sentiment(relevant_posts)

    # Step 3: Display
    display_results(all_results)

    # Step 4: Log
    log_to_csv(all_results)

    print("✅ Sentiment analysis complete!\n")


if __name__ == "__main__":
    main()
