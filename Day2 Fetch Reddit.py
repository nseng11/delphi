"""
Delphi Oracle - Day 2: Reddit Sentiment Data Fetcher
Source: Reddit API

Auth strategy:
  - Streamlit Cloud: uses OAuth credentials from st.secrets (REDDIT_CLIENT_ID etc.)
  - Local dev: falls back to public JSON API (no auth needed)

To enable on Streamlit Cloud, add to your app's Secrets:
    REDDIT_CLIENT_ID     = "your_client_id"
    REDDIT_CLIENT_SECRET = "your_client_secret"
    REDDIT_USER_AGENT    = "DelphiOracle/1.0 by YOUR_USERNAME"

Get credentials at: https://www.reddit.com/prefs/apps  (create a "script" app)
"""

import os
import requests
import json
from datetime import datetime, timezone
from active_market import MARKET_CONFIG


# ── Config ─────────────────────────────────────────────────────────────────────

BASE_HEADERS  = {"User-Agent": "DelphiOracle/1.0 (sentiment research project)"}
KEYWORDS      = MARKET_CONFIG["keywords"]
MAX_POSTS_PER_SUB = 50

SUBREDDITS_NEW = MARKET_CONFIG["subreddits_new"]
SUBREDDITS_HOT = MARKET_CONFIG["subreddits_hot"]


# ── Auth helpers ───────────────────────────────────────────────────────────────

def _get_oauth_token(client_id: str, client_secret: str, user_agent: str) -> str | None:
    """Exchange client credentials for a Reddit OAuth bearer token."""
    try:
        resp = requests.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=(client_id, client_secret),
            data={"grant_type": "client_credentials"},
            headers={"User-Agent": user_agent},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("access_token")
    except Exception as e:
        print(f"  ⚠️  OAuth token error: {e}")
        return None


def _get_reddit_credentials():
    """
    Try to get Reddit OAuth credentials from:
      1. Streamlit secrets (st.secrets)
      2. Environment variables
    Returns (client_id, client_secret, user_agent) or None if unavailable.
    """
    # Try Streamlit secrets first
    try:
        import streamlit as st
        cid    = st.secrets.get("REDDIT_CLIENT_ID")
        csec   = st.secrets.get("REDDIT_CLIENT_SECRET")
        agent  = st.secrets.get("REDDIT_USER_AGENT", "DelphiOracle/1.0")
        if cid and csec:
            return cid, csec, agent
    except Exception:
        pass

    # Fall back to environment variables
    cid   = os.environ.get("REDDIT_CLIENT_ID")
    csec  = os.environ.get("REDDIT_CLIENT_SECRET")
    agent = os.environ.get("REDDIT_USER_AGENT", "DelphiOracle/1.0")
    if cid and csec:
        return cid, csec, agent

    return None


# ── Fetching ───────────────────────────────────────────────────────────────────

def fetch_subreddit_posts(subreddit: str, limit: int = MAX_POSTS_PER_SUB, sort: str = "new") -> list:
    """
    Fetch posts from a subreddit.
    Uses OAuth API if credentials available, falls back to public JSON API.
    """
    creds = _get_reddit_credentials()

    if creds:
        return _fetch_oauth(subreddit, limit, sort, creds)
    else:
        return _fetch_public(subreddit, limit, sort)


def _fetch_oauth(subreddit: str, limit: int, sort: str, creds: tuple) -> list:
    """Fetch using Reddit OAuth API (works from cloud servers)."""
    client_id, client_secret, user_agent = creds
    token = _get_oauth_token(client_id, client_secret, user_agent)
    if not token:
        print(f"  ⚠️  OAuth failed for r/{subreddit}, trying public API...")
        return _fetch_public(subreddit, limit, sort)

    url = f"https://oauth.reddit.com/r/{subreddit}/{sort}"
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": user_agent,
    }
    try:
        print(f"  🔍 Fetching r/{subreddit} (OAuth)...")
        resp = requests.get(url, headers=headers, params={"limit": limit}, timeout=10)
        resp.raise_for_status()
        data  = resp.json()
        posts = data.get("data", {}).get("children", [])
        return [p["data"] for p in posts]
    except Exception as e:
        print(f"  ❌ OAuth fetch error r/{subreddit}: {e}")
        return []


def _fetch_public(subreddit: str, limit: int, sort: str) -> list:
    """Fetch using public JSON API (local dev only — blocked by Reddit on cloud IPs)."""
    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json"
    try:
        print(f"  🔍 Fetching r/{subreddit} (public API)...")
        resp = requests.get(url, headers=BASE_HEADERS, params={"limit": limit}, timeout=10)
        resp.raise_for_status()
        data  = resp.json()
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
    creds = _get_reddit_credentials()
    print(f"            ({'OAuth' if creds else 'Public API - may be blocked on cloud'})")
    print("🔮" * 35 + "\n")

    all_posts      = []
    relevant_posts = []

    print("📡 Scanning subreddits...\n")
    for subreddit in SUBREDDITS_NEW:
        posts = fetch_subreddit_posts(subreddit, sort="new")
        all_posts.extend(posts)
    for subreddit in SUBREDDITS_HOT:
        posts = fetch_subreddit_posts(subreddit, sort="hot")
        all_posts.extend(posts)

    print(f"\n📥 Total posts fetched : {len(all_posts)}")

    for post in all_posts:
        if is_relevant(post):
            relevant_posts.append(post)

    relevant_posts.sort(key=lambda p: p.get("score", 0), reverse=True)

    display_results(relevant_posts)
    print("✅ Reddit fetch complete!\n")


if __name__ == "__main__":
    main()
