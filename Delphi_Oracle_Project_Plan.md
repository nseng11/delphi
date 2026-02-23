# DELPHI
## Prediction Market Sentiment Analysis System

**2-Week MVP Development Plan** — *Last updated: February 22, 2026*

> **Note:** The original PDF project plan is superseded by this document. This file reflects all decisions made during active development.

| | |
|---|---|
| **Project Duration** | 14 Days (2 Weeks) |
| **Estimated Hours** | 35-40 hours total |
| **Target Completion** | Functional MVP with Web Dashboard |
| **Skill Level Required** | Comfortable with Python basics |
| **Budget** | $0 (All free tools and APIs) |

---

## Project Overview

Delphi is a prediction market sentiment analysis system that monitors news sentiment and compares it to current prediction market prices to identify potential mispricings. Named after the Oracle of Delphi, it aims to 'foresee' market movements before they occur.

---

## Active Market

**Best AI Model — End of March 2026**
- Polymarket slug: `which-company-has-the-best-ai-model-end-of-march-751`
- Polymarket event ID: `96022`
- Resolution date: March 31, 2026 (based on lmarena.ai Chatbot Arena leaderboard score)
- Frontrunner: Anthropic at ~63%, Google at ~22%, xAI/OpenAI at ~5-6%
- News source: Google News RSS (per-candidate keyword queries, no auth, works from cloud IPs)

To switch to a different market: edit `active_market.py` (one line change).

---

## Core MVP Features

- [x] Real-time prediction market data fetching (Polymarket API)
- [x] Buy YES / Buy NO prices from live Polymarket order book
- [x] Trading volume per candidate
- [x] News sentiment data fetching (Google News RSS — no auth, works from cloud IPs)
- [x] Flexible market config system (switch markets in one line)
- [x] **Per-candidate** sentiment scoring (not just market-wide aggregate)
- [x] Compound keyword matching per candidate (prevents false positives)
- [x] Signal quality floor (min posts required before signal fires)
- [x] Per-candidate BUY YES / BUY NO / HOLD signals with confidence
- [x] Prediction logging and accuracy tracking
- [x] Web dashboard with auto-refresh visualization
- [x] Historical data charting and performance metrics

---

## Technology Stack

| Category | Technology | Purpose |
|---|---|---|
| Backend | Python 3.14 | Core programming language |
| API Calls | requests library | HTTP requests to APIs |
| Data Processing | pandas | Data manipulation and storage |
| Sentiment Analysis | VADER | NLP sentiment scoring |
| Web Framework | Streamlit | Web dashboard (chosen over Flask for speed) |
| Visualization | Plotly | Interactive charts embedded in Streamlit |
| Data Sources | Polymarket Gamma API | Prediction market prices |
| | Google News RSS | News sentiment data (no auth, no IP restrictions) |

> **Decision log:**
> - Twitter/X API ruled out — restrictive free tier
> - Reddit public API attempted — blocked by Reddit on cloud IPs (AWS/Streamlit Cloud); no workaround without paid API
> - Google News RSS chosen — no credentials, no IP restrictions, aggregates tech news + blogs, ~177 articles/cycle
> - Streamlit chosen over Flask for dashboard — faster to build, Flask planned for post-MVP port
> - VADER chosen for sentiment — fast, no API key needed; LLM upgrade planned post-MVP

---

## File Structure

```
Delphi/
├── active_market.py                        ← change this ONE line to switch markets
├── markets/
│   ├── __init__.py
│   ├── best_ai_model_march_2026.py         ← active market config
│   └── oscars_best_picture.py              ← example config
├── data/
│   ├── best_ai_model_march_2026_sentiment.csv    ← per-candidate sentiment history
│   └── best_ai_model_march_2026_predictions.csv  ← oracle signal history
├── Day1 Fetch Polymarket.py       ✅ complete
├── Day2 Fetch News.py             ✅ complete (Google News RSS fetcher)
├── Day3 Sentiment Engine.py       ✅ complete (per-candidate)
├── Day4 Oracle Logic.py           ✅ complete (BUY YES / BUY NO / HOLD per candidate)
├── Day5 Dashboard.py              ✅ complete (Streamlit)
└── Delphi_Oracle_Project_Plan.md  ← this file
```

---

## Week 1: Core Functionality

**Focus:** Building the data pipeline, sentiment analysis engine, and oracle prediction logic.

### Days 1-2: Data Pipeline Setup ✅ COMPLETE (February 21–22, 2026)

**Goal:** Establish connections to data sources

**Completed tasks:**
- [x] Set up Python 3.14 development environment
- [x] `Day1 Fetch Polymarket.py` — fetches live odds, buy YES/NO prices, and volume via Polymarket Gamma API
- [x] `Day2 Fetch News.py` — fetches relevant news articles via Google News RSS (per-candidate keyword queries; Reddit blocked on cloud IPs)
- [x] Both scripts tested and verified producing live data
- [x] Refactored to flexible market config system (`active_market.py` + `markets/` directory)
- [x] Switched active market from Oscars to **Best AI Model — End of March 2026**
- [x] Fixed wrong event ID/slug (96017 → 96022, old slug → `which-company-has-the-best-ai-model-end-of-march-751`)
- [x] Added buy YES / buy NO prices and trading volume to Day1 output
- [x] Added `min_volume` config to filter zero-volume candidates from display

**Deliverable achieved:** Two working scripts printing live data to terminal ✅

**Key decisions made:**
- Used Google News RSS instead of Reddit — Reddit's public API blocks cloud server IPs (403); Google News has no IP restrictions and no auth requirements
- Switched target market from Oscars 2026 to Best AI Model March 2026 (better fit for ongoing sentiment analysis)
- Built flexible market config system so any Polymarket market can be targeted by changing one line
- Buy YES = `bestAsk` from Polymarket order book; Buy NO = `1 - bestAsk`

---

### Days 3-4: Sentiment Analysis Engine ✅ COMPLETE (February 21–22, 2026)

**Goal:** Convert Reddit post text into actionable per-candidate sentiment scores

**Completed tasks:**
- [x] Installed VADER sentiment library (`pip install vaderSentiment`)
- [x] Built `Day3 Sentiment Engine.py` importing Day1 + Day2 data
- [x] VADER scoring on post title + selftext combined
- [x] Upvote-weighted sentiment aggregation (high-engagement posts count more)
- [x] Normalized score to 0–1 scale; mapped to `bearish / neutral / bullish` labels
- [x] **Redesigned to score sentiment per candidate** — each company gets its own score from its own keyword-filtered posts
- [x] Per-candidate keyword lists in market config using compound phrases to prevent false positives
- [x] Logs one row per candidate to `data/[prefix]_sentiment.csv` with timestamps

**Deliverable achieved:** Script outputting per-candidate weighted sentiment scores + CSV log ✅

**Key decisions made:**
- Market-wide aggregate sentiment was deemed too noisy for multi-candidate markets — per-candidate scoring is the correct approach
- Used upvote-weighting so viral posts dominate over low-quality noise
- Score normalised to (compound + 1) / 2 so 0 = max bearish, 1 = max bullish, 0.5 = neutral
- `analyze_post_sentiment()` function is the designated LLM upgrade point post-MVP
- Compound keyword matching (e.g. `"moonshot ai"` not `"moonshot"`) prevents generic English words from contaminating scores

---

### Days 5-7: Oracle Logic Development ✅ COMPLETE (February 21–22, 2026)

**Goal:** Build the prediction engine that compares per-candidate sentiment vs. price

**Completed tasks:**
- [x] Built `Day4 Oracle Logic.py` combining Polymarket prices + per-candidate sentiment
- [x] Oracle signal rules using thresholds from market config:
  - Sentiment ≥ bullish_threshold AND price < price_low_cutoff AND posts ≥ min_signal_posts → **BUY YES**
  - Sentiment ≤ bearish_threshold AND price > price_high_cutoff AND posts ≥ min_signal_posts → **BUY NO**
  - posts < min_signal_posts → **HOLD** (insufficient data)
  - Otherwise → **HOLD**
- [x] Signals include actual buy YES / buy NO prices from Day1 for immediate actionability
- [x] Confidence scoring: BUY/SELL = distance from threshold; HOLD = distance from nearest edge
- [x] Fixed confidence calculation bug (negative values when sentiment far outside neutral range)
- [x] `min_signal_posts` floor prevents low-data candidates from generating misleading signals
- [x] Logs one row per candidate to `data/[prefix]_predictions.csv`
- [x] Shows last 5 prediction history in terminal

**Deliverable achieved:** Fully functional per-candidate oracle making and logging predictions ✅

**Key decisions made:**
- Single market-wide BUY/SELL signal replaced with per-candidate BUY YES / BUY NO — more actionable for multi-candidate markets
- Oracle thresholds tuned to current market distribution: BUY YES < 20%, BUY NO > 55%
- `min_signal_posts = 5` prevents single viral posts from generating false signals

---

## Week 2: Dashboard & Polish

**Focus:** Creating a professional web interface and preparing for demonstration.

### Days 8-12: Web Dashboard + Visualizations ✅ COMPLETE (February 21, 2026)

**Goal:** Create an accessible, auto-refreshing web interface with charts

**Completed tasks:**
- [x] Installed Streamlit + Plotly
- [x] Built `Day5 Dashboard.py` — full Streamlit app integrating Days 1, 3, and 4 via importlib
- [x] Light SaaS aesthetic (white cards, Inter font, purple brand accent)
- [x] KPI cards row: Oracle Signal (pill badge), Frontrunner, Sentiment, Posts Analyzed
- [x] Sentiment gauge (Plotly Indicator with colored arcs: red/grey/green zones)
- [x] Live Polymarket odds horizontal bar chart
- [x] Historical trend chart: sentiment line + market price dotted line + BUY/SELL markers + threshold lines
- [x] Prediction log table (last 20 entries, color-coded by signal)
- [x] Auto-refresh every 60 seconds via `time.sleep(60)` + `st.rerun()`
- [x] `@st.cache_data(ttl=60)` to avoid redundant API calls during countdown

**Deliverable achieved:** Live dashboard at localhost:8501 ✅

**Run command:** `python -m streamlit run "Day5 Dashboard.py"`

**Key decisions made:**
- Streamlit chosen over Flask — much faster to build; Flask port planned post-MVP
- `importlib.util` used to import files with spaces in their names
- Auto-refresh uses `time.sleep(REFRESH_SECONDS)` + `st.rerun()` (not a per-second loop)

---

### Days 13-14: Testing & Documentation 🔄 IN PROGRESS

**Goal:** Finalize project for demonstration and portfolio

**Tasks:**
- [ ] Run system continuously for 48-72 hours to collect real prediction data
- [ ] Write `README.md` including:
  - Project description and goals
  - Installation instructions (`pip install` commands)
  - How to run each script
  - How to switch markets
  - Interpretation of results
- [ ] Create `requirements.txt` for reproducible setup
- [ ] Record 2-3 minute demo video
- [ ] Take screenshots for portfolio
- [ ] Deploy to VPS (Hostinger KVM2 — Docker + docker-compose)
- [ ] Clean up code and add comments

**Deliverable:** Portfolio-ready project with documentation and demo materials

**Time Investment:** 4-6 hours

---

## Success Criteria

| Category | Minimum Viable | Stretch Goal | Status |
|---|---|---|---|
| Data Collection | Fetches data from 1 market + 1 social source | Multiple markets + sources | ✅ Done |
| Market Flexibility | Hardcoded to one market | Switch markets in one line | ✅ Done (exceeded MVP) |
| Sentiment Analysis | Basic positive/negative/neutral scoring | Nuanced sentiment with confidence | ✅ Done (VADER + confidence scoring) |
| Prediction Logic | Simple threshold-based signals | Adaptive thresholds based on history | ✅ Done (thresholds in market config) |
| Dashboard | Basic HTML with manual refresh | Auto-refresh with multiple charts | ✅ Done (Streamlit, auto-refresh) |
| Accuracy | 50%+ prediction accuracy | 60%+ prediction accuracy | 🔄 Collecting data |
| Documentation | README with setup instructions | Full docs + demo video | ⏳ Pending |

---

## Potential Challenges & Mitigation

| Challenge | Mitigation Strategy |
|---|---|
| API rate limits | Google News RSS used (no auth, generous limits); Polymarket has no rate limits for read operations |
| Inaccurate predictions | Expected for MVP - focus on demonstrating concept, not profitability |
| Time constraints | Prioritize core features; defer polish if needed |
| Technical bugs | Build incrementally; test each component before integration |
| Data quality issues | Implement error handling; validate data before processing |
| Market config mismatch | Print raw question strings from API to verify prefix/suffix format before writing new market config |
| VADER sarcasm/irony | Known limitation — LLM upgrade planned post-MVP via `analyze_post_sentiment()` in Day3 |

---

## Phase 2: GitHub + Deployment ⏳ NEXT

**Goal:** Get the current MVP live and publicly accessible before adding any new features.

- [ ] Create GitHub repo and push all code
- [ ] Add `.gitignore` (exclude `data/`, `__pycache__/`, `.env`)
- [ ] Add `requirements.txt` (already exists — verify it's complete)
- [ ] Deploy to Streamlit Community Cloud (free, connects directly to GitHub repo)
- [ ] Verify dashboard runs correctly on Streamlit Cloud
- [ ] Add live app URL to README

---

## Phase 3: Validated Predictive Model ⏳ FUTURE

**The core problem:** The current signal logic (`IF sentiment > threshold AND price < cutoff`) is a hand-tuned heuristic with no empirical basis. Before trusting any signal, we need to know whether Reddit sentiment actually predicts Polymarket price movement — and if so, by how much, with what lag, and how reliably.

### Step 1 — Data Collection (ongoing, starts now)
- [ ] Run Day4 on a schedule (every 2 hours) to build time-series data
- [ ] Log both sentiment scores AND prices for all candidates at each run
- [ ] Collect at least 2 weeks of data before attempting analysis
- [ ] Target: ~200+ rows per candidate before drawing conclusions

### Step 2 — Correlation & Causality Analysis
- [ ] Build `analysis/correlation.ipynb` Jupyter notebook
- [ ] Compute Pearson/Spearman correlation between `sentiment[t]` and `price[t+k]` for lags k = 0, 2h, 4h, 8h, 24h
- [ ] Run Granger causality test: does sentiment predict price, or does price predict sentiment?
- [ ] Visualise cross-correlation function (CCF) for each candidate
- [ ] Key question: **does Reddit sentiment lead or lag Polymarket prices?**

### Step 3 — Replace Heuristics with a Statistical Model
- [ ] If Granger causality confirmed: fit logistic regression on `P(price_up) = f(sentiment_delta, current_price, posts_count)`
- [ ] Account for the zero-sum constraint: candidates are coupled (probabilities must sum to 1)
- [ ] Use cross-validation to avoid overfitting on limited data
- [ ] Replace hand-tuned thresholds in `oracle` config with model-derived cutoffs

### Step 4 — Backtesting Framework
- [ ] Build `analysis/backtest.py` — replay historical CSV data as if trading in real time
- [ ] Define clear performance metrics: signal accuracy, expected value per trade, Sharpe ratio
- [ ] Compare model-derived signals against the current heuristic baseline
- [ ] Only trust signals that show positive expected value in backtest before acting on live data

### Step 5 — LLM Sentiment Upgrade
- [ ] Replace VADER with Claude API call in `analyze_post_sentiment()` (Day3)
- [ ] Prompt: check relevance (is this post actually about this company's AI model?) + score sentiment
- [ ] Hybrid approach: use VADER for speed, call Claude only for ambiguous/high-upvote posts
- [ ] Re-run correlation analysis with LLM scores to compare against VADER baseline

---

## Future Enhancements (Post-Phase 3)

- **Multi-model consensus** — Run 2-3 LLMs and require agreement before acting on sentiment
- **Auto-generate market configs** — Enter any Polymarket URL; LLM generates the `markets/[slug].py` config automatically (architecture already designed)
- **Additional data sources** — Reddit (if IP restrictions lifted), Twitter/X (if API access obtained)
- **Flask port** — Port dashboard from Streamlit to Flask for more customisation
- **Multi-market dashboard** — Monitor several markets simultaneously; config system already supports this
- **Real-time alerts** — Email/SMS notifications for high-confidence signals
- **VPS deployment** — Host on Hostinger KVM2 via Docker + docker-compose

---

## Important Reminder

**This is a learning project and portfolio piece.** The goal is to demonstrate your ability to build end-to-end data pipelines, not to generate actual trading profits. Prediction accuracy of 50-60% is normal for an MVP and still demonstrates competence in data science, API integration, and full-stack development. The true value is in what you learn during the process and the impressive project you'll have to show employers.
