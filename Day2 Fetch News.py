"""
Delphi Oracle - Day 2: News & Social Sentiment Data Fetcher
Source: Google News RSS (no credentials, no IP restrictions, free)

Strategy:
  Google News RSS aggregates articles from across the web — tech blogs,
  news sites, Reddit threads that made news, etc. It works from any IP
  including Streamlit Cloud, requires zero authentication, and returns
  high-quality signal for AI model discourse.

  We search one query per candidate using their keyword list, then
  aggregate and deduplicate by URL.
"""

import requests
import xml.etree.ElementTree as ET
import urllib.parse
import time
from datetime import datetime, timezone
from active_market import MARKET_CONFIG


# ── Config ─────────────────────────────────────────────────────────────────────

HEADERS        = {"User-Agent": "DelphiOracle/1.0 (sentiment research project)"}
KEYWORDS       = MARKET_CONFIG["keywords"]
CANDIDATES     = MARKET_CONFIG.get("candidates", {})
MAX_PER_QUERY  = 20    # articles per keyword batch (Google News max is ~100)
TIME_WINDOW    = "7d"  # Google News time filter: 1h, 1d, 7d, 30d

# Keep these for backwards compatibility (Day3 imports them)
SUBREDDITS_NEW = MARKET_CONFIG.get("subreddits_new", [])
SUBREDDITS_HOT = MARKET_CONFIG.get("subreddits_hot", [])


# ── Fetching ───────────────────────────────────────────────────────────────────

def _fetch_google_news_rss(query: str, max_results: int = MAX_PER_QUERY) -> list:
    """
    Fetch articles from Google News RSS for a given query string.
    Returns list of dicts with keys matching Reddit post format so
    downstream Day3/Day4 code works unchanged.
    """
    encoded = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded}+when:{TIME_WINDOW}&hl=en-US&gl=US&ceid=US:en"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        root  = ET.fromstring(resp.content)
        items = root.findall(".//item")[:max_results]

        posts = []
        for item in items:
            title      = item.find("title").text   if item.find("title")   is not None else ""
            link       = item.find("link").text     if item.find("link")    is not None else ""
            desc       = item.find("description")
            selftext   = desc.text                  if desc is not None else ""
            pub_date   = item.find("pubDate")
            source_el  = item.find("source")
            source     = source_el.text             if source_el is not None else "News"

            # Parse pubDate → unix timestamp
            created_utc = 0
            if pub_date is not None and pub_date.text:
                try:
                    from email.utils import parsedate_to_datetime
                    created_utc = int(parsedate_to_datetime(pub_date.text).timestamp())
                except Exception:
                    pass

            # Normalise to Reddit-like dict so Day3 VADER scoring works unchanged
            posts.append({
                "id":                        link,         # unique identifier
                "title":                     title,
                "selftext":                  selftext,     # article snippet / description
                "score":                     10,           # synthetic upvote weight
                "num_comments":              0,
                "subreddit_name_prefixed":   f"News/{source}",
                "permalink":                 link,
                "created_utc":               created_utc,
                "url":                       link,
            })
        return posts

    except Exception as e:
        print(f"  ❌ Google News error (query='{query[:50]}'): {e}")
        return []


def fetch_all_posts(keywords: list = None, max_results: int = 100) -> list:
    """
    Fetch news articles for all market keywords using Google News RSS.
    Deduplicates by URL. Returns list of post-like dicts.
    """
    if keywords is None:
        keywords = KEYWORDS

    seen_urls = set()
    all_posts = []

    # Build one query per candidate from their specific keywords
    for candidate, cand_keywords in CANDIDATES.items():
        query = " OR ".join(f'"{kw}"' for kw in cand_keywords[:4])
        print(f"  🔍 Searching news: {candidate} ...")
        posts = _fetch_google_news_rss(query, max_results=MAX_PER_QUERY)
        for post in posts:
            url = post.get("id", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_posts.append(post)
        time.sleep(0.3)   # polite delay

    # Also search broad market terms
    broad_query = " OR ".join(f'"{kw}"' for kw in [
        "best ai model", "ai model comparison", "llm leaderboard",
        "chatbot arena", "frontier model"
    ])
    print(f"  🔍 Searching news: broad market terms ...")
    broad_posts = _fetch_google_news_rss(broad_query, max_results=MAX_PER_QUERY)
    for post in broad_posts:
        url = post.get("id", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            all_posts.append(post)

    # Sort newest first
    all_posts.sort(key=lambda p: p.get("created_utc", 0), reverse=True)
    return all_posts


def fetch_subreddit_posts(subreddit: str, limit: int = 25, sort: str = "new") -> list:
    """
    Compatibility shim — Day3 imports this. Redirects to Google News search
    scoped to the subreddit name as a query term.
    """
    query = f"site:reddit.com/r/{subreddit} ({' OR '.join(KEYWORDS[:4])})"
    print(f"  🔍 Searching news for r/{subreddit} content...")
    return _fetch_google_news_rss(query, max_results=limit)


def is_relevant(post: dict) -> bool:
    """Return True if the article title or description contains a market keyword."""
    text = (post.get("title", "") + " " + post.get("selftext", "")).lower()
    return any(kw.lower() in text for kw in KEYWORDS)


# ── Display ────────────────────────────────────────────────────────────────────

def display_post(rank: int, post: dict) -> None:
    title   = post.get("title", "No title")
    source  = post.get("subreddit_name_prefixed", "News/?")
    score   = post.get("score", 0)
    url     = post.get("url", "")
    created = datetime.fromtimestamp(
        post.get("created_utc", 0), tz=timezone.utc
    ).strftime("%Y-%m-%d %H:%M") if post.get("created_utc") else "Unknown"

    print(f"\n  {rank:2}. [{source}]")
    print(f"      📰 {title}")
    print(f"      🕐 {created} UTC")
    print(f"      🔗 {url[:90]}")


def display_results(relevant_posts: list) -> None:
    print("\n" + "=" * 70)
    print("📊 DELPHI ORACLE - NEWS DATA FEED")
    print("=" * 70)
    print(f"🕐 Retrieved : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Topic     : {MARKET_CONFIG['name']}")
    print(f"📡 Source    : Google News RSS (last {TIME_WINDOW})")
    print("=" * 70)

    if not relevant_posts:
        print("\n⚠️  No relevant articles found.")
        return

    print(f"\n✅ Found {len(relevant_posts)} relevant articles:\n")
    print("-" * 70)
    for rank, post in enumerate(relevant_posts, 1):
        display_post(rank, post)

    print("\n" + "=" * 70)
    print("📊 SUMMARY:")
    print(f"   • Relevant articles found : {len(relevant_posts)}")
    print()


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "🔮" * 35)
    print("        DELPHI ORACLE - NEWS DATA FETCHER")
    print("            (Google News RSS · No Auth Required)")
    print("🔮" * 35 + "\n")

    print("📡 Searching Google News by candidate...\n")
    all_posts = fetch_all_posts()
    print(f"\n📥 Total unique articles fetched : {len(all_posts)}")

    relevant_posts = [p for p in all_posts if is_relevant(p)]
    relevant_posts.sort(key=lambda p: p.get("created_utc", 0), reverse=True)

    display_results(relevant_posts)
    print("✅ News fetch complete!\n")


if __name__ == "__main__":
    main()
