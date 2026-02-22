"""
Delphi Oracle - Day 2: Reddit Sentiment Data Fetcher
Target: Oscars 2026 - Best Picture Winner
Source: Public Reddit API (no credentials required)

Subreddits monitored:
  - r/movies
  - r/Oscars
  - r/entertainment
  - r/PredictionMarkets
  - r/Polymarket
"""

import requests
import json
from datetime import datetime, timezone
from active_market import MARKET_CONFIG


# ── Config ─────────────────────────────────────────────────────────────────────

HEADERS = {"User-Agent": "DelphiOracle/1.0 (sentiment research project)"}

KEYWORDS = MARKET_CONFIG["keywords"]

MAX_POSTS_PER_SUB = 50   # posts to fetch per subreddit (max 100)


# ── Fetching ───────────────────────────────────────────────────────────────────

SUBREDDITS_NEW = MARKET_CONFIG["subreddits_new"]
SUBREDDITS_HOT = MARKET_CONFIG["subreddits_hot"]

def fetch_subreddit_posts(subreddit: str, limit: int = MAX_POSTS_PER_SUB, sort: str = "new") -> list:
    """Fetch posts from a subreddit using the public JSON API."""
    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json"
    params = {"limit": limit}

    try:
        print(f"  🔍 Fetching r/{subreddit}...")
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        posts = data.get("data", {}).get("children", [])
        return [p["data"] for p in posts]

    except requests.exceptions.RequestException as e:
        print(f"  ❌ Error fetching r/{subreddit}: {e}")
        return []


def is_relevant(post: dict) -> bool:
    """Return True if the post title or selftext contains a keyword."""
    text = (post.get("title", "") + " " + post.get("selftext", "")).lower()
    return any(kw.lower() in text for kw in KEYWORDS)


# ── Display ────────────────────────────────────────────────────────────────────

def display_post(rank: int, post: dict) -> None:
    """Pretty-print a single post."""
    title     = post.get("title", "No title")
    subreddit = post.get("subreddit_name_prefixed", "r/?")
    score     = post.get("score", 0)
    comments  = post.get("num_comments", 0)
    url       = "https://reddit.com" + post.get("permalink", "")
    created   = datetime.fromtimestamp(post.get("created_utc", 0), tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

    print(f"\n  {rank:2}. [{subreddit}]")
    print(f"      📰 {title}")
    print(f"      ⬆ {score} points  |  💬 {comments} comments  |  🕐 {created} UTC")
    print(f"      🔗 {url}")


def display_results(relevant_posts: list) -> None:
    """Display all relevant posts with a summary."""
    print("\n" + "=" * 70)
    print("📊 DELPHI ORACLE - REDDIT DATA FEED")
    print("=" * 70)
    print(f"🕐 Retrieved: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Topic: {MARKET_CONFIG['name']}")
    all_subs = SUBREDDITS_NEW + SUBREDDITS_HOT
    print(f"📡 Sources: {', '.join(['r/' + s for s in all_subs])}")
    print("=" * 70)

    if not relevant_posts:
        print("\n⚠️  No relevant posts found. Try expanding KEYWORDS or SUBREDDITS.")
        return

    print(f"\n✅ Found {len(relevant_posts)} relevant posts:\n")
    print("-" * 70)

    for rank, post in enumerate(relevant_posts, 1):
        display_post(rank, post)

    # ── Summary stats
    total_score    = sum(p.get("score", 0) for p in relevant_posts)
    total_comments = sum(p.get("num_comments", 0) for p in relevant_posts)
    top_post       = max(relevant_posts, key=lambda p: p.get("score", 0))

    print("\n" + "=" * 70)
    print("📊 SUMMARY:")
    print(f"   • Relevant posts found : {len(relevant_posts)}")
    print(f"   • Total upvotes        : {total_score:,}")
    print(f"   • Total comments       : {total_comments:,}")
    print(f"   • Most upvoted post    : {top_post.get('title', '')[:60]}...")
    print(f"   • Top post score       : {top_post.get('score', 0):,} upvotes")
    print()


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "🔮" * 35)
    print("        DELPHI ORACLE - REDDIT DATA FETCHER")
    print("            (Public API · No Auth Required)")
    print("🔮" * 35 + "\n")

    all_posts     = []
    relevant_posts = []

    # Fetch from all subreddits
    print("📡 Scanning subreddits...\n")
    for subreddit in SUBREDDITS_NEW:
        posts = fetch_subreddit_posts(subreddit, sort="new")
        all_posts.extend(posts)
    for subreddit in SUBREDDITS_HOT:
        posts = fetch_subreddit_posts(subreddit, sort="hot")
        all_posts.extend(posts)

    print(f"\n📥 Total posts fetched : {len(all_posts)}")

    # Filter for relevance
    for post in all_posts:
        if is_relevant(post):
            relevant_posts.append(post)

    # Sort by score descending
    relevant_posts.sort(key=lambda p: p.get("score", 0), reverse=True)

    # Display
    display_results(relevant_posts)
    print("✅ Reddit fetch complete!\n")


if __name__ == "__main__":
    main()
