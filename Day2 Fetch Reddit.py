"""
Delphi Oracle - Day 2: Reddit Sentiment Data Fetcher
Source: Reddit public search API (no credentials required)

Strategy:
  Instead of fetching subreddit feeds (blocked by Reddit on cloud IPs),
  we search Reddit globally by keyword. This works from Streamlit Cloud
  without any API credentials and is actually better targeted — we only
  retrieve posts that explicitly mention our market's topics.

  Search queries are built from the market config's keyword list,
  batched into groups so we don't exceed URL length limits.
"""

import requests
import time
from datetime import datetime, timezone
from active_market import MARKET_CONFIG


# ── Config ─────────────────────────────────────────────────────────────────────

HEADERS           = {"User-Agent": "DelphiOracle/1.0 (sentiment research project)"}
KEYWORDS          = MARKET_CONFIG["keywords"]
MAX_RESULTS       = 100    # total posts to retrieve per search batch
KEYWORDS_PER_QUERY = 6    # number of keywords ORed together per API call
SORT              = "new"  # "new" | "hot" | "relevance" | "top"
TIME_FILTER       = "week" # "hour" | "day" | "week" | "month" | "year" | "all"

# Keep these for backwards compatibility (Day3/Day5 import them)
SUBREDDITS_NEW = MARKET_CONFIG.get("subreddits_new", [])
SUBREDDITS_HOT = MARKET_CONFIG.get("subreddits_hot", [])


# ── Fetching ───────────────────────────────────────────────────────────────────

def _search_reddit(query: str, limit: int = 25, sort: str = SORT,
                   time_filter: str = TIME_FILTER) -> list:
    """
    Call Reddit's global search endpoint with a query string.
    Returns a list of raw post dicts. No auth required.
    """
    url = "https://www.reddit.com/search.json"
    params = {
        "q":        query,
        "sort":     sort,
        "t":        time_filter,
        "limit":    min(limit, 100),
        "type":     "link",
    }
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        children = resp.json().get("data", {}).get("children", [])
        return [c["data"] for c in children]
    except Exception as e:
        print(f"  ❌ Search error (query='{query[:40]}...'): {e}")
        return []


def fetch_all_posts(keywords: list = None, max_results: int = MAX_RESULTS) -> list:
    """
    Search Reddit for all market-relevant posts by batching keywords into OR queries.
    Deduplicates by post ID.

    Args:
        keywords:    List of search terms. Defaults to MARKET_CONFIG["keywords"].
        max_results: Approximate cap on total posts fetched.

    Returns:
        List of unique post dicts, sorted newest first.
    """
    if keywords is None:
        keywords = KEYWORDS

    seen_ids = set()
    all_posts = []

    # Batch keywords into OR queries
    batches = [
        keywords[i: i + KEYWORDS_PER_QUERY]
        for i in range(0, len(keywords), KEYWORDS_PER_QUERY)
    ]

    per_batch = max(10, max_results // max(len(batches), 1))

    for batch in batches:
        query = " OR ".join(f'"{kw}"' for kw in batch)
        print(f"  🔍 Searching: {query[:70]}...")
        posts = _search_reddit(query, limit=per_batch)
        for post in posts:
            pid = post.get("id")
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                all_posts.append(post)
        # Small delay to be a polite API citizen
        time.sleep(0.5)

    # Sort newest first
    all_posts.sort(key=lambda p: p.get("created_utc", 0), reverse=True)
    return all_posts


def fetch_subreddit_posts(subreddit: str, limit: int = 25, sort: str = "new") -> list:
    """
    Compatibility shim — Day3/Day5 call this per-subreddit.
    On Streamlit Cloud we redirect to keyword search instead of subreddit feeds.
    Locally the subreddit feed usually works, so we try it first.
    """
    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json"
    try:
        resp = requests.get(url, headers=HEADERS, params={"limit": limit}, timeout=10)
        if resp.status_code == 200:
            children = resp.json().get("data", {}).get("children", [])
            posts = [c["data"] for c in children]
            if posts:
                print(f"  🔍 Fetched r/{subreddit} ({len(posts)} posts)")
                return posts
        # 403 / empty = cloud IP blocked; fall through to search
        print(f"  ⚠️  r/{subreddit} feed blocked or empty — using search fallback")
    except Exception:
        print(f"  ⚠️  r/{subreddit} feed error — using search fallback")

    # Fallback: search within this subreddit
    query = " OR ".join(f'"{kw}"' for kw in KEYWORDS[:KEYWORDS_PER_QUERY])
    url_search = f"https://www.reddit.com/r/{subreddit}/search.json"
    try:
        resp = requests.get(url_search, headers=HEADERS,
                            params={"q": query, "sort": sort, "limit": limit,
                                    "restrict_sr": "true", "t": TIME_FILTER},
                            timeout=10)
        resp.raise_for_status()
        children = resp.json().get("data", {}).get("children", [])
        posts = [c["data"] for c in children]
        print(f"  🔍 Searched r/{subreddit} ({len(posts)} posts)")
        return posts
    except Exception as e:
        print(f"  ❌ Search fallback error for r/{subreddit}: {e}")
        return []


def is_relevant(post: dict) -> bool:
    """Return True if the post title or selftext contains a market keyword."""
    text = (post.get("title", "") + " " + post.get("selftext", "")).lower()
    return any(kw.lower() in text for kw in KEYWORDS)


# ── Display ────────────────────────────────────────────────────────────────────

def display_post(rank: int, post: dict) -> None:
    title     = post.get("title", "No title")
    subreddit = post.get("subreddit_name_prefixed", "r/?")
    score     = post.get("score", 0)
    comments  = post.get("num_comments", 0)
    url       = "https://reddit.com" + post.get("permalink", "")
    created   = datetime.fromtimestamp(
        post.get("created_utc", 0), tz=timezone.utc
    ).strftime("%Y-%m-%d %H:%M")

    print(f"\n  {rank:2}. [{subreddit}]")
    print(f"      📰 {title}")
    print(f"      ⬆ {score} points  |  💬 {comments} comments  |  🕐 {created} UTC")
    print(f"      🔗 {url}")


def display_results(relevant_posts: list) -> None:
    print("\n" + "=" * 70)
    print("📊 DELPHI ORACLE - REDDIT DATA FEED")
    print("=" * 70)
    print(f"🕐 Retrieved : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Topic     : {MARKET_CONFIG['name']}")
    print(f"🔑 Keywords  : {len(KEYWORDS)} terms across {len(KEYWORDS)//KEYWORDS_PER_QUERY +1} search batches")
    print("=" * 70)

    if not relevant_posts:
        print("\n⚠️  No relevant posts found. Try expanding KEYWORDS or TIME_FILTER.")
        return

    print(f"\n✅ Found {len(relevant_posts)} relevant posts:\n")
    print("-" * 70)
    for rank, post in enumerate(relevant_posts, 1):
        display_post(rank, post)

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
    print("            (Keyword Search · No Auth Required)")
    print("🔮" * 35 + "\n")

    print("📡 Searching Reddit by keyword...\n")
    all_posts = fetch_all_posts()
    print(f"\n📥 Total unique posts fetched : {len(all_posts)}")

    # All posts from search are already relevant, but filter to be safe
    relevant_posts = [p for p in all_posts if is_relevant(p)]
    relevant_posts.sort(key=lambda p: p.get("score", 0), reverse=True)

    display_results(relevant_posts)
    print("✅ Reddit fetch complete!\n")


if __name__ == "__main__":
    main()
