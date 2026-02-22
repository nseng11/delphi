"""
Delphi Oracle - Day 5: Streamlit Dashboard
Live web interface combining Polymarket prices, Reddit sentiment, and Oracle signals.

Run with:
    python -m streamlit run "Day5 Dashboard.py"

Features:
  - Per-candidate oracle signals (BUY YES / BUY NO / HOLD) with confidence
  - Live Polymarket odds, buy YES/NO prices, and volume for all contenders
  - Per-candidate sentiment scores and post counts
  - Historical sentiment + price chart (from CSV logs)
  - Prediction history table
  - Auto-refresh every 60 seconds
"""

import os
import importlib.util
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime

from active_market import MARKET_CONFIG


# ── Import pipeline modules ──────────────────────────────────────────────────────

def _import_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_base = os.path.dirname(os.path.abspath(__file__))
_day1 = _import_file("day1", os.path.join(_base, "Day1 Fetch Polymarket.py"))
_day3 = _import_file("day3", os.path.join(_base, "Day3 Sentiment Engine.py"))
_day4 = _import_file("day4", os.path.join(_base, "Day4 Oracle Logic.py"))

fetch_market_by_slug             = _day1.fetch_market_by_slug
get_candidates                   = _day1.get_candidates
fetch_all_posts                  = _day3.fetch_all_posts
is_relevant                      = _day3.is_relevant
compute_all_candidates_sentiment = _day3.compute_all_candidates_sentiment
generate_signal                  = _day4.generate_signal
log_predictions                  = _day4.log_predictions

SENTIMENT_CSV   = os.path.join(_base, "data", f"{MARKET_CONFIG['data_prefix']}_sentiment.csv")
PREDICTIONS_CSV = os.path.join(_base, "data", f"{MARKET_CONFIG['data_prefix']}_predictions.csv")

BULLISH_THRESHOLD = MARKET_CONFIG["sentiment"]["bullish_threshold"]
BEARISH_THRESHOLD = MARKET_CONFIG["sentiment"]["bearish_threshold"]
MIN_SIGNAL_POSTS  = MARKET_CONFIG.get("min_signal_posts", 3)
REFRESH_SECONDS   = 60


# ── Page config ──────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Delphi Oracle",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS: Light SaaS theme ─────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background-color: #F8F9FB !important;
        font-family: 'Inter', sans-serif;
    }
    [data-testid="stHeader"] { background-color: #F8F9FB !important; }
    [data-testid="stSidebar"] { background-color: #F1F3F5 !important; }

    .delphi-logo {
        display: flex; align-items: center; gap: 12px; margin-bottom: 4px;
    }
    .delphi-wordmark {
        font-size: 2rem; font-weight: 800; color: #7B2FBE;
        letter-spacing: -0.5px; line-height: 1;
    }
    .market-badge {
        display: inline-block; background: #EDE9F6; color: #7B2FBE;
        font-size: 0.78rem; font-weight: 600; padding: 4px 12px;
        border-radius: 999px; border: 1px solid #D4C5EE; letter-spacing: 0.01em;
    }
    .delphi-subtitle {
        color: #9CA3AF; font-size: 0.9rem; font-weight: 400;
        margin-top: 2px; margin-bottom: 0;
    }

    /* ── KPI Cards ── */
    .kpi-card {
        background: #FFFFFF; border-radius: 12px; padding: 20px 22px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.07), 0 4px 12px rgba(0,0,0,0.04);
        border: 1px solid #E9EAEC; height: 100%; min-height: 110px;
    }
    .kpi-label {
        font-size: 0.7rem; font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.08em; color: #9CA3AF; margin-bottom: 10px;
    }
    .kpi-value { font-size: 1.55rem; font-weight: 700; color: #111827; line-height: 1.2; }
    .kpi-sub   { font-size: 0.78rem; color: #6B7280; margin-top: 4px; font-weight: 500; }
    .kpi-timestamp { font-size: 0.7rem; color: #D1D5DB; margin-top: 6px; }

    /* ── Signal pill badges ── */
    .signal-pill {
        display: inline-flex; align-items: center; gap: 6px;
        font-size: 1.0rem; font-weight: 700; padding: 5px 14px;
        border-radius: 999px; letter-spacing: 0.03em;
    }
    .signal-pill.buy-yes { background: #DCFCE7; color: #15803D; border: 1px solid #BBF7D0; }
    .signal-pill.buy-no  { background: #FEE2E2; color: #DC2626; border: 1px solid #FECACA; }
    .signal-pill.hold    { background: #FEF3C7; color: #B45309; border: 1px solid #FDE68A; }
    .signal-pill.nodata  { background: #F3F4F6; color: #9CA3AF; border: 1px solid #E5E7EB; }
    .pill-dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }
    .buy-yes .pill-dot { background: #16A34A; }
    .buy-no  .pill-dot { background: #DC2626; }
    .hold    .pill-dot { background: #D97706; }
    .nodata  .pill-dot { background: #9CA3AF; }

    /* ── Section titles ── */
    .section-title {
        font-size: 1rem; font-weight: 700; color: #1F2937;
        border-left: 3px solid #7B2FBE; padding-left: 10px;
        margin-top: 8px; margin-bottom: 4px;
    }

    hr { border-color: #E9EAEC !important; margin: 20px 0 !important; }

    .refresh-bar {
        font-size: 0.75rem; color: #D1D5DB; text-align: center; padding: 8px 0 2px;
    }

    [data-testid="stDataFrame"] {
        border-radius: 10px; overflow: hidden; border: 1px solid #E9EAEC;
    }
</style>
""", unsafe_allow_html=True)


# ── Data fetching (cached for 60s) ───────────────────────────────────────────────

@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False)
def fetch_live_data():
    """Fetch all live data and generate per-candidate signals. Cached for 60s."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Day1: Polymarket prices
    event_data       = fetch_market_by_slug(MARKET_CONFIG["slug"])
    market_candidates = get_candidates(event_data, min_probability=0.0) if event_data else []

    # Build price lookup
    price_lookup = {
        c["name"]: {
            "price":   c["probability"] / 100,
            "buy_yes": c.get("buy_yes", 0),
            "buy_no":  c.get("buy_no", 0),
            "volume":  c.get("volume", 0),
        }
        for c in market_candidates
    }

    # Day2/3: Reddit keyword search + per-candidate sentiment
    # fetch_all_posts() uses Reddit's search endpoint (works from cloud IPs, no auth needed)
    reddit_error = None
    try:
        all_posts = fetch_all_posts()
    except Exception as e:
        reddit_error = str(e)
        all_posts = []
    relevant          = [p for p in all_posts if is_relevant(p)]
    sentiment_results = compute_all_candidates_sentiment(relevant)

    # Day4: per-candidate signals
    candidate_signals = []
    for candidate, sent_result in sentiment_results.items():
        if candidate not in price_lookup:
            continue
        prices = price_lookup[candidate]
        score  = sent_result["normalized_score"] if sent_result else None
        label  = sent_result["label"]             if sent_result else "no_data"
        posts  = sent_result["posts_analyzed"]    if sent_result else 0
        signal = generate_signal(score, prices["price"], posts_analyzed=posts)

        candidate_signals.append({
            "name":            candidate,
            "price":           prices["price"],
            "buy_yes":         prices["buy_yes"],
            "buy_no":          prices["buy_no"],
            "volume":          prices["volume"],
            "sentiment_score": score,
            "sentiment_label": label,
            "posts_analyzed":  posts,
            "signal":          signal,
        })

    candidate_signals.sort(key=lambda x: x["price"], reverse=True)

    # Log to CSV
    if candidate_signals:
        log_predictions(timestamp, candidate_signals)

    return {
        "candidates":        candidate_signals,
        "market_candidates": market_candidates,
        "posts_fetched":     len(all_posts),
        "posts_count":       len(relevant),
        "fetched_at":        datetime.now().strftime("%H:%M:%S"),
        "timestamp":         timestamp,
        "reddit_error":      reddit_error,
    }


def load_sentiment_history() -> pd.DataFrame:
    if not os.path.isfile(SENTIMENT_CSV):
        return pd.DataFrame()
    df = pd.read_csv(SENTIMENT_CSV)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def load_prediction_history() -> pd.DataFrame:
    if not os.path.isfile(PREDICTIONS_CSV):
        return pd.DataFrame()
    df = pd.read_csv(PREDICTIONS_CSV)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


# ── Chart builders ───────────────────────────────────────────────────────────────

_CHART_LAYOUT = dict(
    paper_bgcolor="#FFFFFF",
    plot_bgcolor="#F8F9FB",
    font=dict(family="Inter, sans-serif", color="#374151", size=12),
)


def make_odds_bar(candidates: list) -> go.Figure:
    """Horizontal bar chart of market odds with buy prices and volume."""
    shown  = [c for c in candidates if c.get("volume", 0) >= MARKET_CONFIG.get("min_volume", 0)]
    names  = [c["name"] for c in shown]
    probs  = [c["price"] * 100 for c in shown]
    colors = ["#7B2FBE" if i == 0 else "#A78BFA" if i == 1 else "#C4B5FD"
              for i in range(len(names))]

    def _vol(v):
        if v >= 1_000_000: return f"${v/1_000_000:.1f}M vol"
        if v >= 1_000:     return f"${v/1_000:.1f}K vol"
        return f"${v:.0f} vol"

    text = [
        f"{p:.1f}%  ·  Yes ${c['buy_yes']:.3f} / No ${c['buy_no']:.3f}  ·  {_vol(c.get('volume', 0))}"
        for p, c in zip(probs, shown)
    ]

    fig = go.Figure(go.Bar(
        x=probs, y=names, orientation="h",
        marker_color=colors, marker_line=dict(width=0),
        text=text, textposition="outside",
        textfont=dict(color="#374151", size=11, family="Inter"),
    ))
    fig.update_layout(
        **_CHART_LAYOUT,
        title=dict(text="Live Polymarket Odds  (buy prices & volume shown)", font=dict(size=13, color="#6B7280"), x=0),
        xaxis=dict(range=[0, 130], ticksuffix="%", gridcolor="#E9EAEC",
                   showline=False, tickfont=dict(color="#9CA3AF")),
        yaxis=dict(autorange="reversed", showgrid=False, tickfont=dict(color="#374151", size=12)),
        height=max(240, len(shown) * 52),
        margin=dict(l=10, r=10, t=44, b=16),
    )
    return fig


def make_sentiment_table(candidates: list) -> pd.DataFrame:
    """Build a DataFrame for the per-candidate sentiment table."""
    rows = []
    for c in candidates:
        score = c["sentiment_score"]
        sig   = c["signal"]["signal"]
        rows.append({
            "Candidate":  c["name"],
            "Price":      f"{c['price']*100:.1f}%",
            "Sentiment":  f"{score:.3f}" if score is not None else "N/A",
            "Posts":      c["posts_analyzed"],
            "Label":      c["sentiment_label"],
            "Signal":     sig,
            "Buy YES":    f"${c['buy_yes']:.3f}",
            "Buy NO":     f"${c['buy_no']:.3f}",
        })
    return pd.DataFrame(rows)


def make_history_chart(sentiment_df: pd.DataFrame, predictions_df: pd.DataFrame,
                       candidate: str = None, hours: int = None) -> go.Figure:
    """Sentiment + price history for a specific candidate, optionally filtered by time range."""
    fig = go.Figure()

    # Apply time range filter
    if hours is not None:
        cutoff = pd.Timestamp.now() - pd.Timedelta(hours=hours)
        if not sentiment_df.empty:
            sentiment_df = sentiment_df[sentiment_df["timestamp"] >= cutoff].copy()
        if not predictions_df.empty:
            predictions_df = predictions_df[predictions_df["timestamp"] >= cutoff].copy()

    if not sentiment_df.empty and "candidate" in sentiment_df.columns:
        cands = sentiment_df["candidate"].unique().tolist()
        sel   = candidate if candidate in cands else (cands[0] if cands else None)
        if sel:
            cdf = sentiment_df[sentiment_df["candidate"] == sel].copy()
            fig.add_trace(go.Scatter(
                x=cdf["timestamp"], y=cdf["normalized_score"].astype(float),
                name=f"{sel} Sentiment",
                line=dict(color="#7B2FBE", width=2.5),
                fill="tozeroy", fillcolor="rgba(123,47,190,0.06)",
            ))

    if not predictions_df.empty and "candidate" in predictions_df.columns:
        cands = predictions_df["candidate"].unique().tolist()
        sel   = candidate if candidate in cands else (cands[0] if cands else None)
        if sel:
            pdf = predictions_df[predictions_df["candidate"] == sel].copy()
            pdf["price_val"] = pd.to_numeric(pdf["market_price_pct"], errors="coerce") / 100
            fig.add_trace(go.Scatter(
                x=pdf["timestamp"], y=pdf["price_val"],
                name=f"{sel} Market Price",
                line=dict(color="#3B82F6", width=2, dash="dot"),
            ))
            for sig, color, symbol in [("BUY YES", "#16A34A", "triangle-up"),
                                        ("BUY NO",  "#DC2626", "triangle-down")]:
                mask = pdf["signal"] == sig
                if mask.any():
                    fig.add_trace(go.Scatter(
                        x=pdf.loc[mask, "timestamp"], y=pdf.loc[mask, "price_val"],
                        mode="markers", name=sig,
                        marker=dict(color=color, size=11, symbol=symbol,
                                    line=dict(color="white", width=1.5)),
                    ))

    fig.add_hline(y=BULLISH_THRESHOLD, line_dash="dash", line_color="#16A34A", opacity=0.5,
                  annotation_text="Bullish", annotation_font=dict(color="#16A34A", size=10),
                  annotation_position="right")
    fig.add_hline(y=BEARISH_THRESHOLD, line_dash="dash", line_color="#DC2626", opacity=0.5,
                  annotation_text="Bearish", annotation_font=dict(color="#DC2626", size=10),
                  annotation_position="right")

    fig.update_layout(
        **_CHART_LAYOUT,
        title=dict(text="Sentiment & Market Price Over Time", font=dict(size=13, color="#6B7280"), x=0),
        xaxis=dict(gridcolor="#E9EAEC", showline=False, tickfont=dict(color="#9CA3AF")),
        yaxis=dict(range=[0, 1.08], tickformat=".0%", gridcolor="#E9EAEC",
                   showline=False, tickfont=dict(color="#9CA3AF")),
        legend=dict(bgcolor="white", bordercolor="#E9EAEC", borderwidth=1,
                    font=dict(color="#374151", size=11)),
        height=360,
        margin=dict(l=16, r=90, t=44, b=16),
    )
    return fig


# ── HTML helpers ─────────────────────────────────────────────────────────────────

def _signal_pill(sig: str) -> str:
    mapping = {
        "BUY YES": ("buy-yes", "▲", "BUY YES"),
        "BUY NO":  ("buy-no",  "▼", "BUY NO"),
        "HOLD":    ("hold",    "●", "HOLD"),
    }
    cls, icon, label = mapping.get(sig, ("nodata", "—", sig))
    return (f'<span class="signal-pill {cls}">'
            f'<span class="pill-dot"></span>{icon} {label}</span>')

def _kpi_card(label: str, value_html: str, sub: str = "", timestamp: str = "") -> str:
    ts = f'<div class="kpi-timestamp">{timestamp}</div>' if timestamp else ""
    sb = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value_html}</div>
        {sb}{ts}
    </div>"""

def _section_title(text: str) -> str:
    return f'<div class="section-title">{text}</div>'


# ── Main dashboard layout ────────────────────────────────────────────────────────

def main():

    # ── Header
    st.markdown(f"""
    <div class="delphi-logo">
        <span class="delphi-wordmark">🔮 Delphi Oracle</span>
        <span class="market-badge">{MARKET_CONFIG['name']}</span>
    </div>
    <p class="delphi-subtitle">Prediction market sentiment intelligence · Live analysis</p>
    """, unsafe_allow_html=True)
    st.divider()

    # ── Fetch live data
    with st.spinner("Fetching live data..."):
        data = fetch_live_data()

    candidates = data["candidates"]

    # ── Debug info (always visible when posts = 0)
    if data.get("reddit_error"):
        st.error(f"⚠️ Reddit fetch error: {data['reddit_error']}")
    elif data.get("posts_fetched", 0) == 0:
        st.warning("⚠️ Reddit returned 0 posts. Check the debug panel below.")

    with st.expander("🔧 Debug info", expanded=(data.get("posts_fetched", 0) == 0)):
        st.json({
            "posts_fetched":  data.get("posts_fetched", 0),
            "posts_relevant": data.get("posts_count", 0),
            "reddit_error":   data.get("reddit_error"),
            "candidates_from_polymarket": len(data.get("market_candidates", [])),
            "fetched_at":     data.get("fetched_at"),
        })

    # ── Derive summary KPIs
    frontrunner    = candidates[0] if candidates else None
    actionable     = [c for c in candidates if c["signal"]["signal"] not in ("HOLD",)]
    total_posts    = data["posts_count"]

    # ── Row 1: KPI cards
    col1, col2, col3, col4 = st.columns(4, gap="medium")

    with col1:
        if actionable:
            # Show the highest-confidence actionable signal
            top = max(actionable, key=lambda c: c["signal"]["confidence"])
            html = _kpi_card(
                "Top Signal",
                _signal_pill(top["signal"]["signal"]),
                sub=f"{top['name']} · conf {top['signal']['confidence']:.3f}",
            )
        else:
            html = _kpi_card("Top Signal", _signal_pill("HOLD"), sub="No divergence detected")
        st.markdown(html, unsafe_allow_html=True)

    with col2:
        if frontrunner:
            html = _kpi_card(
                "Frontrunner",
                frontrunner["name"][:26],
                sub=f"{frontrunner['price']*100:.1f}%  ·  Yes ${frontrunner['buy_yes']:.3f}",
            )
        else:
            html = _kpi_card("Frontrunner", "—")
        st.markdown(html, unsafe_allow_html=True)

    with col3:
        n_signals = len(actionable)
        html = _kpi_card(
            "Active Signals",
            str(n_signals),
            sub=f"of {len(candidates)} candidates",
        )
        st.markdown(html, unsafe_allow_html=True)

    with col4:
        fetched = data.get("posts_fetched", 0)
        sub_txt = f"{fetched} fetched · {total_posts} relevant" if fetched != total_posts else "Reddit posts this cycle"
        html = _kpi_card(
            "Posts Analyzed",
            str(total_posts),
            sub=sub_txt,
            timestamp=f"Updated {data['fetched_at']}",
        )
        st.markdown(html, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 2: Odds chart + Sentiment table
    col_left, col_right = st.columns([3, 2], gap="medium")

    with col_left:
        st.markdown(_section_title("Market Odds"), unsafe_allow_html=True)
        if candidates:
            fig = make_odds_bar(candidates)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Could not load Polymarket data.")

    with col_right:
        st.markdown(_section_title("Per-Candidate Signals"), unsafe_allow_html=True)
        if candidates:
            df = make_sentiment_table(candidates)

            def color_signal(val):
                if val == "BUY YES": return "color: #15803D; font-weight: 700"
                if val == "BUY NO":  return "color: #DC2626; font-weight: 700"
                return "color: #B45309"

            def color_label(val):
                if val == "bullish": return "color: #15803D"
                if val == "bearish": return "color: #DC2626"
                return "color: #9CA3AF"

            st.dataframe(
                df.style
                  .map(color_signal, subset=["Signal"])
                  .map(color_label,  subset=["Label"]),
                use_container_width=True,
                hide_index=True,
            )

    # ── Row 3: Historical chart (candidate selector + time range)
    st.markdown(_section_title("Historical Trends"), unsafe_allow_html=True)
    sentiment_df   = load_sentiment_history()
    predictions_df = load_prediction_history()

    if sentiment_df.empty and predictions_df.empty:
        st.info("No historical data yet — run the Oracle a few times to build history.")
    else:
        candidate_names = []
        if not predictions_df.empty and "candidate" in predictions_df.columns:
            candidate_names = sorted(predictions_df["candidate"].unique().tolist())

        ctrl_left, ctrl_right = st.columns([2, 3], gap="medium")

        with ctrl_left:
            selected = None
            if candidate_names:
                selected = st.selectbox("Candidate:", candidate_names, index=0)

        with ctrl_right:
            TIME_RANGES = {"1H": 1, "6H": 6, "1D": 24, "1W": 168, "ALL": None}
            range_label = st.radio(
                "Time range:", list(TIME_RANGES.keys()),
                index=4, horizontal=True, label_visibility="collapsed"
            )
            selected_hours = TIME_RANGES[range_label]

        fig = make_history_chart(sentiment_df, predictions_df,
                                 candidate=selected, hours=selected_hours)
        st.plotly_chart(fig, use_container_width=True)

    # ── Row 4: Prediction log
    if not predictions_df.empty:
        st.markdown(_section_title("Prediction Log"), unsafe_allow_html=True)
        cols_available = predictions_df.columns.tolist()

        # Support both old schema (frontrunner) and new schema (candidate)
        name_col  = "candidate"  if "candidate"       in cols_available else "frontrunner"
        price_col = "market_price_pct"

        show_cols = [c for c in ["timestamp", name_col, price_col,
                                  "sentiment_score", "sentiment_label",
                                  "signal", "confidence"] if c in cols_available]

        display_df = (predictions_df
                      .sort_values("timestamp", ascending=False)
                      .head(20)[show_cols]
                      .copy())
        display_df.columns = ["Time", "Candidate", "Price %",
                               "Sentiment", "Label", "Signal", "Confidence"][:len(show_cols)]

        def color_signal(val):
            if val == "BUY YES": return "color: #15803D; font-weight: 700"
            if val == "BUY NO":  return "color: #DC2626; font-weight: 700"
            return "color: #B45309; font-weight: 600"

        st.dataframe(
            display_df.style.map(color_signal, subset=["Signal"]),
            use_container_width=True,
            hide_index=True,
        )

    # ── Footer / refresh
    st.divider()
    foot_left, foot_mid, foot_right = st.columns([3, 1, 3])
    with foot_mid:
        if st.button("🔄 Refresh now", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    st.markdown(
        f'<div class="refresh-bar">Cache refreshes every {REFRESH_SECONDS}s · '
        f'Last fetch: {data["fetched_at"]}</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
