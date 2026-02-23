# ============================================================
# Delphi - Market Config: Oscars 2026 Best Picture
# ============================================================
# Copy this file to create a new market config.
# Edit all values below, then point active_market.py at it.
# ============================================================

MARKET_CONFIG = {

    # --- Identity ---
    "name":        "Oscars 2026 - Best Picture Winner",
    "slug":        "oscars-2026-best-picture-winner",
    "data_prefix": "oscars_best_picture",   # used for CSV filenames in data/

    # --- Polymarket question parsing ---
    # Each Polymarket market phrases its questions differently.
    # Set strip_prefix to the text BEFORE the candidate/film name.
    # Set strip_suffix to the text AFTER the candidate/film name.
    # Example question: "Will Sinners win Best Picture at the 98th Academy Awards?"
    #   strip_prefix "Will "  →  "Sinners win Best Picture at the 98th Academy Awards?"
    #   strip_suffix " win Best Picture at the 98th Academy Awards?"  →  "Sinners"
    "question_parsing": {
        "strip_prefix": "Will ",
        "strip_suffix": " win Best Picture at the 98th Academy Awards?",
    },

    # --- News search config (subreddits kept for compatibility shim in Day2) ---
    "subreddits_new": ["movies", "Oscars", "entertainment", "criterion"],
    "subreddits_hot": ["PredictionMarkets", "Polymarket"],

    "keywords": [
        # Event
        "oscars",
        "academy awards",
        "98th academy",
        # Category
        "best picture",
        "best picture winner",
        # Nominees
        "one battle after another",
        "sinners",
        "hamnet",
        "marty supreme",
        "sentimental value",
        "frankenstein",
        "bugonia",
        "train dreams",
        # Directors & talent
        "paul thomas anderson",
        "ryan coogler",
        "chloe zhao",
        "josh safdie",
        "guillermo del toro",
        "timothee chalamet",
        "michael b jordan",
        # Awards season terms
        "oscar winner",
        "oscar prediction",
        "oscar odds",
        "awards season",
        "oscar nominated",
    ],

    # --- Sentiment thresholds (used by Day3 Sentiment Engine) ---
    # Score is normalized -1 to +1.
    # Above bullish_threshold = market sentiment favors frontrunner.
    # Below bearish_threshold = market sentiment goes against frontrunner.
    "sentiment": {
        "bullish_threshold": 0.65,
        "bearish_threshold": 0.35,
    },

    # --- Oracle thresholds (used by Day4 Oracle Logic) ---
    # If sentiment is bullish AND market price is below price_low_cutoff → signal UP
    # If sentiment is bearish AND market price is above price_high_cutoff → signal DOWN
    "oracle": {
        "price_low_cutoff":  0.60,
        "price_high_cutoff": 0.75,
    },
}
