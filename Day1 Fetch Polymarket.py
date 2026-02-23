"""
Delphi - Day 1: Polymarket Data Fetcher
Fetches live market odds for the active market config.

Supports two Polymarket market structures:
  - AMM markets: outcomePrices per candidate (e.g. Oscars Best Picture)
  - Order-book markets: bestBid/lastTradePrice per Yes/No sub-market (e.g. Best AI Model)
"""

import requests
import json
from datetime import datetime
from active_market import MARKET_CONFIG

# Polymarket Gamma API
GAMMA_API = "https://gamma-api.polymarket.com"


def extract_candidate_name(question, parsing_config):
    """Generic candidate name extractor using market config prefix/suffix."""
    prefix = parsing_config["strip_prefix"]
    suffix = parsing_config["strip_suffix"]
    if question.startswith(prefix) and question.endswith(suffix):
        return question[len(prefix):-len(suffix)].strip()
    return None


def fetch_market_by_slug(slug):
    """
    Fetch market event data. Tries three strategies in order:
      1. Slug query (works for most active markets)
      2. Slug query with closed=true (catches inactive/restricted markets)
      3. Direct event_id lookup from MARKET_CONFIG (ultimate fallback)
    """
    url = f"{GAMMA_API}/events"

    try:
        print(f"🔍 Fetching data from Polymarket...")
        print(f"   URL: {url}")
        print(f"   Slug: {slug}\n")

        # Strategy 1: slug only
        response = requests.get(url, params={"slug": slug}, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data:
            return data[0]

        # Strategy 2: include closed/inactive
        response = requests.get(url, params={"slug": slug, "closed": "true"}, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data:
            return data[0]

        # Strategy 3: direct event_id (set in market config as fallback)
        event_id = MARKET_CONFIG.get("event_id")
        if event_id:
            response = requests.get(f"{GAMMA_API}/events/{event_id}", timeout=10)
            response.raise_for_status()
            data = response.json()
            if data:
                return data

        print("❌ No market found with that slug")
        return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching data: {e}")
        return None


def _extract_candidates_from_markets(markets, min_probability=0.0) -> list:
    """
    Internal helper: extract candidate list from market objects.

    Handles two market structures:
      A) AMM (outcomePrices present): one market per candidate, outcomePrices[0] = win %
         e.g. Oscars Best Picture — "Will Sinners win Best Picture?" → 13.7%

      B) Order-book (outcomePrices absent): one Yes/No market per candidate,
         probability = bestBid of Yes side (or lastTradePrice if no bids yet)
         e.g. Best AI Model — "Will OpenAI have the best AI model?" Yes/No
         groupItemTitle = clean company name ("OpenAI")
    """
    candidates = []

    for market in markets:
        question     = market.get('question', '')
        outcomes_raw = market.get('outcomes', '[]')
        prices_raw   = market.get('outcomePrices', None)
        volume       = float(market.get('volumeNum', 0) or 0)

        # ── Structure A: AMM market (outcomePrices present) ──────────────────
        if prices_raw is not None:
            try:
                outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw
                prices   = json.loads(prices_raw)   if isinstance(prices_raw,   str) else prices_raw

                name_part = extract_candidate_name(question, MARKET_CONFIG["question_parsing"])
                if name_part is None:
                    # Fall back to groupItemTitle for AMM markets
                    name_part = market.get('groupItemTitle', '').strip()
                if not name_part:
                    continue

                best_ask = float(market.get('bestAsk', 0) or 0)

                for outcome, price in zip(outcomes, prices):
                    if outcome.lower() == "yes":
                        probability = float(price) * 100
                        buy_yes = round(best_ask, 4) if best_ask else round(float(price), 4)
                        buy_no  = round(1 - buy_yes, 4)
                        if probability >= min_probability:
                            candidates.append({
                                'name':        name_part,
                                'probability': round(probability, 1),
                                'buy_yes':     buy_yes,
                                'buy_no':      buy_no,
                                'volume':      volume,
                            })
                        break

            except (json.JSONDecodeError, ValueError):
                continue

        # ── Structure B: Order-book market (no outcomePrices) ────────────────
        else:
            # Use groupItemTitle as the clean candidate name (already parsed by Polymarket)
            name_part = market.get('groupItemTitle', '').strip()
            if not name_part:
                # Fall back to question parsing if groupItemTitle missing
                name_part = extract_candidate_name(question, MARKET_CONFIG["question_parsing"])
            if not name_part:
                continue

            # Best available price: bestBid → lastTradePrice → 0
            best_bid        = float(market.get('bestBid', 0) or 0)
            best_ask        = float(market.get('bestAsk', 0) or 0)
            last_trade      = float(market.get('lastTradePrice', 0) or 0)
            probability     = (best_bid or last_trade) * 100

            # buy Yes = bestAsk (cost to buy a Yes share at the ask)
            # buy No  = 1 - bestAsk (complement, since Yes + No = $1)
            buy_yes = round(best_ask, 4)
            buy_no  = round(1 - best_ask, 4)

            if probability >= min_probability:
                candidates.append({
                    'name':        name_part,
                    'probability': round(probability, 1),
                    'buy_yes':     buy_yes,
                    'buy_no':      buy_no,
                    'volume':      volume,
                })

    candidates.sort(key=lambda x: x['probability'], reverse=True)
    return candidates


def get_candidates(event_data, min_probability=0.0) -> list:
    """
    Return sorted list of {name, probability} dicts (silent — no printing).
    Used by Day3, Day4, Day5 to get clean programmatic data.
    min_probability defaults to 0.0 so pre-launch order-book markets still show all candidates.
    """
    if not event_data:
        return []
    return _extract_candidates_from_markets(
        event_data.get('markets', []), min_probability=min_probability
    )


def parse_market_data(event_data, min_probability=0.0):
    """Parse and display market data for the active market."""
    if not event_data:
        return

    print("=" * 70)
    print("📊 DELPHI - MARKET DATA")
    print("=" * 70)
    print(f"\n🎯 Market  : {MARKET_CONFIG['name']}")
    print(f"📅 Retrieved: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔗 Slug    : {event_data.get('slug', 'N/A')}")

    markets    = event_data.get('markets', [])
    candidates = _extract_candidates_from_markets(markets, min_probability=min_probability)

    # Filter by min_volume from market config (0 = show all)
    min_volume = MARKET_CONFIG.get("min_volume", 0)
    shown = [c for c in candidates if c['volume'] >= min_volume]

    print(f"\n📈 Sub-markets found : {len(markets)}")
    print(f"🏁 Candidates shown : {len(shown)} (of {len(candidates)}, min volume ${min_volume:,.0f})")

    # Detect whether prices are live or all zero (pre-launch order-book market)
    all_zero = all(c['probability'] == 0.0 for c in shown)
    if all_zero and shown:
        print(f"⚠️  No live prices yet — market hasn't opened for trading")
        print(f"   Showing all candidates with 0.0% until trading begins\n")
    else:
        print()

    print(f"🏆 TOP CONTENDERS — {MARKET_CONFIG['name'].upper()}")
    print("-" * 92)
    print("{:<4}{:<3} {:<30} {:>6}  {:>8}  {:>8}  {:>12}".format("", "", "Candidate", "Odds", "Buy YES", "Buy NO", "Volume ($)"))
    print("-" * 92)

    if not shown:
        print(f"⚠️  No candidates found")
        return

    for rank, candidate in enumerate(shown, 1):
        prob    = candidate['probability']
        medal   = "🥇 " if rank == 1 else "🥈 " if rank == 2 else "🥉 " if rank == 3 else "   "
        buy_yes = candidate.get('buy_yes')
        buy_no  = candidate.get('buy_no')
        vol     = candidate.get('volume', 0)
        yes_str = "${:.3f}".format(buy_yes) if buy_yes is not None else "  N/A "
        no_str  = "${:.3f}".format(buy_no)  if buy_no  is not None else "  N/A "
        vol_str = "${:,.0f}".format(vol)
        print("{}{:2}. {:<30} {:>5.1f}%  {:>8}  {:>8}  {:>12}".format(medal, rank, candidate['name'], prob, yes_str, no_str, vol_str))

    print("\n" + "=" * 70)
    print("\n📊 SUMMARY:")
    print(f"   • {len(shown)} candidates with volume >= ${min_volume:,.0f}")
    if not all_zero:
        print(f"   • Frontrunner : {shown[0]['name']} at {shown[0]['probability']:.1f}%")
        if len(shown) > 1:
            gap = shown[0]['probability'] - shown[1]['probability']
            print(f"   • Gap to 2nd  : {gap:.1f} percentage points")
    print()


def main():
    print("\n" + "🔮" * 35)
    print("        DELPHI - POLYMARKET DATA FETCHER")
    print("🔮" * 35 + "\n")

    event_data = fetch_market_by_slug(MARKET_CONFIG["slug"])

    if event_data:
        parse_market_data(event_data)
        print("✅ Data fetch complete!\n")
    else:
        print("❌ Failed to fetch market data\n")


if __name__ == "__main__":
    main()
