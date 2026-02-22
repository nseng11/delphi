# 🔮 Delphi Oracle

> **Prediction market sentiment analysis — identify mispricings before the market corrects.**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-red?logo=streamlit)
![License](https://img.shields.io/badge/License-MIT-green)

---

## What is Delphi Oracle?

Delphi Oracle monitors news sentiment around a Polymarket prediction market and compares it to the current implied odds. When sentiment for a specific candidate diverges significantly from their market price, the Oracle flags it as a **BUY YES** (underpriced), **BUY NO** (overpriced), or **HOLD** signal.

Sentiment is scored **per candidate** — not as a single market-wide aggregate. This means the system can simultaneously flag Google as underpriced while flagging Anthropic as overpriced within the same market.

Named after the Oracle of Delphi — it doesn't guarantee the future, but it sees patterns others miss.

---

## How It Works

```
┌─────────────────┐     ┌──────────────────────┐
│  Polymarket API  │     │   Google News RSS     │
│  (live odds +    │     │  (no key, no IP block)│
│   buy prices)    │     │  tech news · blogs    │
└────────┬─────────┘     └────────┬─────────────┘
         │                        │
         ▼                        ▼
┌─────────────────────────────────────────────┐
│           Day3 Sentiment Engine              │
│   Per-candidate VADER scoring                │
│   Article-weighted · min article floor       │
│   Output: score per candidate (0.0 – 1.0)   │
└───────────────────────┬─────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────┐
│             Day4 Oracle Logic                │
│   Per-candidate sentiment vs. price          │
│   Output: BUY YES / BUY NO / HOLD           │
│           + confidence + buy prices          │
└───────────────────────┬─────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────┐
│           Day5 Streamlit Dashboard           │
│   Live KPIs · Odds · Signals · History      │
│   Auto-refreshes every 60 seconds           │
└─────────────────────────────────────────────┘
```

---

## Dashboard Preview

> 📸 *Screenshot coming soon — run the dashboard locally to see it in action.*

Key panels:
- **Oracle Signals** — per-candidate BUY YES / BUY NO / HOLD with confidence
- **Live Odds** — Polymarket probability bar chart with buy YES/NO prices and volume
- **Sentiment Table** — per-candidate sentiment scores and article counts
- **Historical Trends** — sentiment + price over time with signal markers
- **Prediction Log** — timestamped record of every oracle signal

---

## Quickstart

### 1. Clone or download the project

```bash
git clone https://github.com/your-username/delphi-oracle.git
cd delphi-oracle
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Launch the dashboard

```bash
python -m streamlit run "Day5 Dashboard.py"
```

The dashboard opens automatically at **http://localhost:8501**

> **Note:** Use `python -m streamlit run`, not `python "Day5 Dashboard.py"` — the latter runs it as a plain Python script and won't open the browser UI.

---

## Running Individual Scripts

| Script | What it does | Run command |
|---|---|---|
| `Day1 Fetch Polymarket.py` | Fetches live odds, buy YES/NO prices, and volume from Polymarket | `python "Day1 Fetch Polymarket.py"` |
| `Day2 Fetch Reddit.py` | Fetches relevant news articles via Google News RSS (per candidate) | `python "Day2 Fetch Reddit.py"` |
| `Day3 Sentiment Engine.py` | Runs per-candidate VADER sentiment on news articles, logs to CSV | `python "Day3 Sentiment Engine.py"` |
| `Day4 Oracle Logic.py` | Combines per-candidate sentiment + price → BUY YES/BUY NO/HOLD signals | `python "Day4 Oracle Logic.py"` |
| `Day5 Dashboard.py` | Full live dashboard (runs the entire pipeline) | `python -m streamlit run "Day5 Dashboard.py"` |

---

## Switching Markets

To analyse a different Polymarket market, edit **one line** in `active_market.py`:

```python
# active_market.py — this is the ONLY file you change
from markets.best_ai_model_march_2026 import MARKET_CONFIG   # ← swap this line
```

Create a new market config by copying an existing file from `markets/` and filling in:

| Field | Description |
|---|---|
| `name` | Human-readable market name |
| `slug` | Polymarket URL slug (from the market URL) |
| `event_id` | Polymarket event ID (fallback if slug query returns empty) |
| `data_prefix` | Prefix for CSV filenames in `data/` |
| `min_volume` | Hide candidates with less than this total trading volume (e.g. `1.0`) |
| `min_signal_posts` | Minimum articles required before a BUY/SELL signal fires (e.g. `5`) |
| `question_parsing` | `strip_prefix` / `strip_suffix` to extract candidate names from API question strings |
| `subreddits_new` | Subreddits (kept for config compatibility, used as fallback search terms) |
| `subreddits_hot` | Subreddits (kept for config compatibility, used as fallback search terms) |
| `candidates` | Dict mapping each candidate name to their specific search keywords |
| `keywords` | Flat list (derived from `candidates`) used by Day2 for broad article fetching |
| `sentiment.bullish_threshold` | Normalized score above which sentiment is bullish (e.g. `0.60`) |
| `sentiment.bearish_threshold` | Normalized score below which sentiment is bearish (e.g. `0.40`) |
| `oracle.price_low_cutoff` | BUY YES signal if price is below this (e.g. `0.20` = 20%) |
| `oracle.price_high_cutoff` | BUY NO signal if price is above this (e.g. `0.55` = 55%) |

---

## Project Structure

```
Delphi/
├── active_market.py                        ← change ONE line to switch markets
├── markets/
│   ├── __init__.py
│   ├── best_ai_model_march_2026.py         ← active market config
│   └── oscars_best_picture.py              ← example config (copy to add new markets)
├── data/
│   ├── best_ai_model_march_2026_sentiment.csv    ← per-candidate sentiment history
│   └── best_ai_model_march_2026_predictions.csv  ← oracle signal history
├── Day1 Fetch Polymarket.py                ← Polymarket API fetcher
├── Day2 Fetch Reddit.py                    ← Google News RSS fetcher (per-candidate)
├── Day3 Sentiment Engine.py                ← per-candidate VADER sentiment analysis
├── Day4 Oracle Logic.py                    ← BUY YES/BUY NO/HOLD signal generation
├── Day5 Dashboard.py                       ← Streamlit live dashboard
├── requirements.txt
└── README.md
```

---

## Signal Logic

The Oracle compares **per-candidate news sentiment** against that **candidate's Polymarket price**:

| Condition | Signal | Meaning |
|---|---|---|
| Sentiment ≥ bullish_threshold **AND** Price < price_low_cutoff **AND** articles ≥ min_signal_posts | 📈 **BUY YES** | News is bullish but market hasn't priced it in — candidate may be underpriced |
| Sentiment ≤ bearish_threshold **AND** Price > price_high_cutoff **AND** articles ≥ min_signal_posts | 📉 **BUY NO** | News is bearish but market is still pricing them high — candidate may be overpriced |
| articles < min_signal_posts | ⚠️ **HOLD** | Not enough news data to trust the signal |
| All other conditions | ➡️ **HOLD** | No significant divergence detected |

**Confidence** measures signal strength:
- For BUY YES/NO: sum of distances from both thresholds (larger = stronger signal, capped at 1.0)
- For HOLD: how centred sentiment is between the two thresholds (1.0 = perfectly neutral)

All thresholds are configurable per market in the market config file.

---

## Signal Quality Controls

Two mechanisms prevent low-quality signals from firing:

**1. `min_volume` (Day1)** — candidates with no meaningful trading activity are hidden from the display entirely. Set in the market config (e.g. `"min_volume": 1.0`).

**2. `min_signal_posts` (Day4)** — a BUY YES or BUY NO signal only fires if the candidate had at least this many qualifying news articles in the current fetch cycle. Prevents a single article from triggering a trade signal. Set in the market config (e.g. `"min_signal_posts": 5`).

**3. Specific candidate keywords** — each candidate has its own keyword list, using compound phrases (e.g. `"moonshot ai"` instead of `"moonshot"`, `"baidu ernie"` instead of `"ernie"`) to prevent generic English words from contaminating sentiment scores. Each candidate's Google News query uses their top 4 keywords.

---

## Interpreting Results

| Metric | What it means |
|---|---|
| **Sentiment Score** | VADER sentiment score per candidate averaged across matching articles, normalised to 0–1. `0.5` = neutral. |
| **Posts Analyzed** | Number of news articles that matched this candidate's keywords. Low numbers = less reliable signal. |
| **Market Price** | The current Polymarket implied probability (e.g. `63.3%` = $0.633 to buy a Yes share). |
| **Buy YES price** | Cost per share to buy a Yes position (bestAsk from Polymarket order book). |
| **Buy NO price** | Cost per share to buy a No position (`1 - bestAsk`). |
| **Oracle Signal** | The divergence conclusion for this candidate. Only acts when both sentiment AND price cross their thresholds simultaneously AND min post count is met. |
| **Confidence** | How strongly the current reading satisfies the signal conditions. Ranges 0–1. |

---

## Roadmap

- [x] Real-time prediction market data fetching (Polymarket Gamma API)
- [x] Buy YES / Buy NO prices from live order book
- [x] Trading volume per candidate
- [x] Per-candidate news sentiment (not just market-wide)
- [x] Signal quality floor (min articles before signal fires)
- [x] Compound keyword matching to prevent false positives
- [x] Google News RSS as data source (works from Streamlit Cloud, no auth required)
- [ ] **LLM sentiment layer** — replace VADER with Claude for relevance filtering + better sarcasm/irony detection
- [ ] **Multi-model consensus** — require 2–3 LLMs to agree before generating a signal
- [ ] **Auto-generate market configs** — paste a Polymarket URL, LLM writes the config file automatically
- [ ] **Additional data sources** — Twitter/X, Reddit (when accessible)
- [ ] **Flask port** — port dashboard from Streamlit to Flask for more control
- [ ] **Real-time alerts** — email/SMS for high-confidence signals
- [ ] **VPS deployment** — Docker + docker-compose on Hostinger KVM2
- [ ] **Backtesting** — replay historical data to measure signal accuracy

---

## Disclaimer

**This is a learning project and portfolio piece.** Nothing in this project constitutes financial advice. Prediction accuracy of 50–60% is normal and expected for an MVP of this type. The goal is to demonstrate competence in building end-to-end data pipelines — not to generate trading profits.
