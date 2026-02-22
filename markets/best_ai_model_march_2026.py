# ============================================================
# Delphi Oracle - Market Config: Best AI Model End of March 2026
# ============================================================
# Copy this file to create a new market config.
# Edit all values below, then point active_market.py at it.
#
# To activate:
#   In active_market.py, change the import to:
#   from markets.best_ai_model_march_2026 import MARKET_CONFIG
# ============================================================

MARKET_CONFIG = {

    # --- Identity ---
    "name":        "Best AI Model - End of March 2026",
    "slug":        "which-company-has-the-best-ai-model-end-of-march-751",
    "event_id":    96022,   # fallback: direct ID lookup if slug query returns empty
    "data_prefix": "best_ai_model_march_2026",  # used for CSV filenames in data/
    "min_volume":  1.0,     # hide candidates with less than $1 total trading volume

    # --- Polymarket question parsing ---
    # Each sub-market question: "Will [Company] have the best AI model at the end of March 2026?"
    #   strip_prefix "Will "  →  "[Company] have the best AI model at the end of March 2026?"
    #   strip_suffix " have the best AI model at the end of March 2026?"  →  "[Company]"
    "question_parsing": {
        "strip_prefix": "Will ",
        "strip_suffix": " have the best AI model at the end of March 2026?",
    },

    # --- Reddit config ---
    # subreddits_new: high-volume AI discourse subs (fetched by recency)
    # subreddits_hot: prediction market subs (fetched by hot/trending)
    "subreddits_new": [
        "artificial",
        "MachineLearning",
        "ChatGPT",
        "ClaudeAI",
        "Gemini",
        "LocalLLaMA",
    ],
    "subreddits_hot": [
        "PredictionMarkets",
        "Polymarket",
    ],

    # --- Per-candidate keywords ---
    # Used by Day3 to score sentiment for each company individually.
    # A post counts toward a candidate if any of its keywords appear in the title/body.
    # Day2 fetches using a merged flat list of all keywords below.
    #
    # IMPORTANT — avoid generic words that contaminate sentiment:
    #   - "moonshot" matches "this is a moonshot idea" → false bullish signal
    #   - "google" matches any Google news unrelated to AI → noisy
    #   - "ernie" matches people named Ernie → false positives
    # Prefer specific compound terms: "moonshot ai", "google gemini", "baidu ernie"
    "candidates": {
        "Anthropic": [
            "anthropic",
            "claude 3",
            "claude 4",
            "claude opus",
            "claude sonnet",
            "claude haiku",
        ],
        "Google": [
            "google deepmind",
            "google gemini",
            "google ai",
            "gemini 2",
            "gemini ultra",
            "gemini pro",
            "gemini flash",
            "deepmind",
        ],
        "xAI": [
            "xai",
            "x.ai",
            "grok 3",
            "grok3",
            "grok ai",
        ],
        "OpenAI": [
            "openai",
            "gpt-5",
            "gpt5",
            "o3 model",
            "o4 model",
            "chatgpt",
        ],
        "DeepSeek": [
            "deepseek",
            "deep seek",
            "deepseek v3",
            "deepseek r2",
            "deepseek r1",
        ],
        "Alibaba": [
            "alibaba qwen",
            "qwen3",
            "qwen 3",
            "qwen2",
            "alibaba ai",
            "tongyi",
        ],
        "Z.ai": [
            "z.ai",
            "z ai model",
        ],
        "Baidu": [
            "baidu ernie",
            "ernie bot",
            "baidu ai",
            "wenxin",
        ],
        "Moonshot": [
            "moonshot ai",
            "kimi ai",
            "kimi k2",
            "kimi model",
        ],
        "Meituan": [
            "meituan ai",
            "meituan model",
        ],
        "Mistral": [
            "mistral ai",
            "mistral large",
            "mistral model",
            "le chat mistral",
            "mixtral",
        ],
    },

    # Flat keyword list derived from candidates above — used by Day2 for broad Reddit fetching.
    # Keep this in sync with the candidates dict.
    "keywords": [
        "anthropic", "claude opus", "claude sonnet", "claude 4",
        "google deepmind", "google gemini", "gemini 2", "deepmind",
        "xai", "grok 3", "grok ai",
        "openai", "gpt-5", "chatgpt", "o3 model",
        "deepseek", "deepseek v3", "deepseek r1",
        "alibaba qwen", "qwen3", "qwen2", "tongyi",
        "z.ai",
        "baidu ernie", "ernie bot", "wenxin",
        "moonshot ai", "kimi ai",
        "meituan ai",
        "mistral ai", "mistral large", "mixtral",
        "chatbot arena", "lmsys", "llm leaderboard", "lmarena",
        "arena score", "best ai model", "frontier model",
        "ai race", "best llm", "llm comparison",
        "swe-bench", "aider benchmark",
    ],

    # --- Signal quality floor ---
    # Minimum number of Reddit posts required before a BUY YES / BUY NO signal fires.
    # Prevents low-data candidates (1-2 posts) from generating misleading signals.
    # Candidates below this threshold show their sentiment score but output HOLD.
    "min_signal_posts": 5,

    # --- Sentiment thresholds (used by Day3 Sentiment Engine) ---
    # Score is normalized 0 to 1 (0.5 = neutral).
    # AI discourse is perpetually tribal (OpenAI vs Anthropic vs Google fans),
    # so a tighter band (0.60/0.40 vs Oscars' 0.65/0.35) fires signals on
    # moderate consensus rather than requiring extreme agreement.
    "sentiment": {
        "bullish_threshold": 0.60,
        "bearish_threshold": 0.40,
    },

    # --- Oracle thresholds (used by Day4 Oracle Logic) ---
    # Current distribution (Feb 2026): Anthropic ~63%, Google ~22%, xAI/OpenAI ~5%.
    # BUY YES if: sentiment bullish AND price < 20%
    #   → targets realistic challengers (Google and below) that Reddit thinks are underpriced
    # BUY NO if: sentiment bearish AND price > 55%
    #   → targets Anthropic if Reddit sentiment turns against it
    # Signals on sub-1% longshots (Moonshot, Alibaba, etc.) are filtered out by the
    # price_low_cutoff — they'll never fire BUY YES unless they trade above 0% and below 20%.
    "oracle": {
        "price_low_cutoff":  0.20,
        "price_high_cutoff": 0.55,
    },
}
