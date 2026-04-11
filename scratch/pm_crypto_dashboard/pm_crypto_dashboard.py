import sys, os
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

from dotenv import load_dotenv
load_dotenv(r'C:\QuantLab\Data_Lab\.env', override=True)

from datetime import datetime, timedelta
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import requests
from plotly.subplots import make_subplots


GREEN = "#26a69a"
LT_GREEN = "#66bb6a"
YELLOW = "#ffa726"
DK_ORANGE = "#ef6c00"
RED = "#ef5350"
BLUE = "#42a5f5"
PURPLE = "#ab47bc"
GOLD = "#ffd700"
BG = "#111111"
CARD_BG = "#1a1a1a"
TEXT = "#e0e0e0"
MUTED = "#888888"
BORDER = "#2a2a2a"

OUTPUT_DIR = Path(r"C:\QuantLab\Data_Lab\scratch\pm_crypto_dashboard")
OUTPUT_FILE = OUTPUT_DIR / "index.html"


def _empty_series() -> pd.Series:
    return pd.Series(dtype=float)


def _sanitize_index(series: pd.Series) -> pd.Series:
    if series is None or series.empty:
        return _empty_series()

    cleaned = series.copy().dropna()
    cleaned.index = pd.to_datetime(cleaned.index)
    if getattr(cleaned.index, "tz", None) is not None:
        cleaned.index = cleaned.index.tz_localize(None)
    return cleaned.sort_index()


def _daily_last(series: pd.Series) -> pd.Series:
    cleaned = _sanitize_index(series)
    if cleaned.empty:
        return _empty_series()
    daily = cleaned.groupby(cleaned.index.normalize()).last()
    daily.index = pd.to_datetime(daily.index)
    return daily.sort_index()


def _safe_float(value):
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_json_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []
    return []


def fetch_polymarket_market(market_id: str) -> dict:
    """
    Returns dict with keys:
      current_yes_prob  float 0-100
      current_no_prob   float 0-100
      question          str
      history           pd.Series (date index, yes probability 0-100)
      volume            float
      error             str or None
    """
    result = {
        "current_yes_prob": None,
        "current_no_prob": None,
        "question": "Unknown",
        "history": _empty_series(),
        "volume": 0.0,
        "error": None,
    }

    try:
        url = f"https://gamma-api.polymarket.com/markets/{market_id}"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            result["error"] = f"HTTP {resp.status_code}"
            return result

        data = resp.json()
        market = data[0] if isinstance(data, list) and data else data
        market = market or {}

        result["question"] = market.get("question", market.get("title", "Unknown"))
        result["volume"] = float(market.get("volume", 0) or 0)

        prices = market.get("outcomePrices", market.get("outcome_prices", []))
        prices = _safe_json_list(prices) if isinstance(prices, str) else prices
        if prices and len(prices) >= 2:
            yes = _safe_float(prices[0])
            no = _safe_float(prices[1])
            if yes is not None:
                result["current_yes_prob"] = yes * 100
            if no is not None:
                result["current_no_prob"] = no * 100

        tokens = market.get("tokens", []) or []
        yes_token = None
        for token in tokens:
            if str(token.get("outcome", "")).lower() == "yes":
                yes_token = token.get("token_id", token.get("id", ""))
                break
        if not yes_token and tokens:
            yes_token = tokens[0].get("token_id", tokens[0].get("id", ""))

        if not yes_token:
            outcomes = [str(item).lower() for item in _safe_json_list(market.get("outcomes"))]
            clob_token_ids = _safe_json_list(market.get("clobTokenIds"))
            if outcomes and clob_token_ids and len(outcomes) == len(clob_token_ids):
                for outcome, token_id in zip(outcomes, clob_token_ids):
                    if outcome == "yes":
                        yes_token = token_id
                        break
                if not yes_token:
                    yes_token = clob_token_ids[0]

        # Prefer the local indexed loader for stable trailing history.
        # This repo already maintains Polymarket parquet indexes, which are
        # materially better for 7d/90d history than the thin public CLOB window.
        try:
            from tools.prediction_markets.pm_data_loader import get_market_probability

            local_history = get_market_probability(str(market_id), days=90)
            local_history = _sanitize_index(local_history)
            if not local_history.empty:
                result["history"] = local_history
        except Exception:
            pass

        if yes_token and len(result["history"]) < 8:
            hist_url = (
                "https://clob.polymarket.com/prices-history"
                f"?market={yes_token}&interval=max&fidelity=1"
            )
            hist_resp = requests.get(hist_url, timeout=10)
            if hist_resp.status_code == 200:
                hist_data = hist_resp.json()
                history_points = hist_data.get("history", []) or []
                if history_points:
                    dates = []
                    prices_list = []
                    for point in history_points:
                        ts = point.get("t", point.get("timestamp"))
                        price = point.get("p", point.get("price"))
                        if ts and price is not None:
                            parsed_price = _safe_float(price)
                            if parsed_price is None:
                                continue
                            dates.append(pd.Timestamp(ts, unit="s"))
                            prices_list.append(parsed_price * 100)
                    if dates:
                        live_history = _daily_last(pd.Series(prices_list, index=dates))
                        if len(live_history) >= len(result["history"]):
                            result["history"] = live_history
    except Exception as exc:
        result["error"] = str(exc)

    return result


def fetch_fear_greed() -> dict:
    """
    Fetches Crypto Fear & Greed Index from alternative.me.

    Returns dict:
      current_value    int 0-100
      classification   str e.g. "Fear", "Greed"
      history          pd.Series (date index, value 0-100, last 90 days)
      error            str or None
    """
    result = {
        "current_value": None,
        "classification": "Unknown",
        "history": _empty_series(),
        "error": None,
    }

    try:
        url = "https://api.alternative.me/fng/?limit=90&format=json"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            result["error"] = f"HTTP {resp.status_code}"
            return result

        data = resp.json()
        entries = data.get("data", []) or []
        if entries:
            result["current_value"] = int(entries[0]["value"])
            result["classification"] = entries[0]["value_classification"]

            dates = []
            values = []
            for entry in entries:
                ts = int(entry["timestamp"])
                dates.append(pd.Timestamp(ts, unit="s"))
                values.append(int(entry["value"]))

            result["history"] = _sanitize_index(pd.Series(values, index=dates))
    except Exception as exc:
        result["error"] = str(exc)

    return result


def fetch_btc_spy_data() -> dict:
    """
    Fetches BTC (via BITO ETF) and SPY prices.
    Uses DataRouter for both.
    Returns 252 days of daily closes.

    Returns dict:
      bito    pd.Series (date index, close prices)
      spy     pd.Series (date index, close prices)
      error   str or None
    """
    result = {
        "bito": _empty_series(),
        "spy": _empty_series(),
        "error": None,
    }

    try:
        from shared.data_router import DataRouter

        start = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        bito_df = DataRouter.get_price_data("BITO", start)
        spy_df = DataRouter.get_price_data("SPY", start)

        if bito_df is not None and not bito_df.empty:
            close_col = "Close" if "Close" in bito_df.columns else bito_df.columns[0]
            result["bito"] = _sanitize_index(bito_df[close_col].dropna())

        if spy_df is not None and not spy_df.empty:
            close_col = "Close" if "Close" in spy_df.columns else spy_df.columns[0]
            result["spy"] = _sanitize_index(spy_df[close_col].dropna())
    except Exception as exc:
        result["error"] = str(exc)

    return result


def fetch_btc_dominance() -> dict:
    """
    Fetches Bitcoin dominance % from CoinGecko.
    Uses the free public API.

    Returns dict:
      current    float (e.g. 54.2 means 54.2%)
      history    pd.Series (date index, % values, last 90 days if available)
      error      str or None
    """
    result = {
        "current": None,
        "history": _empty_series(),
        "error": None,
    }

    try:
        url = "https://api.coingecko.com/api/v3/global"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            dominance = data.get("market_cap_percentage", {}).get("btc")
            if dominance is not None:
                result["current"] = float(dominance)

        hist_url = (
            "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
            "?vs_currency=usd&days=90&interval=daily"
        )
        hist_resp = requests.get(hist_url, timeout=15)
        if hist_resp.status_code == 200:
            hist_data = hist_resp.json()
            prices = hist_data.get("prices", []) or []
            if prices:
                dates = [pd.Timestamp(price[0], unit="ms") for price in prices]
                values = [price[1] for price in prices]
                result["history"] = _sanitize_index(pd.Series(values, index=dates))
    except Exception as exc:
        result["error"] = str(exc)

    return result


def get_fed_cut_implication(yes_prob: float, roc_7d: float) -> dict:
    """yes_prob is 0-100. roc_7d is change in percentage points over 7 days."""
    if yes_prob is None:
        return {
            "text": "Data unavailable",
            "color": MUTED,
            "action": "No actionable signal",
        }

    if roc_7d is not None and roc_7d >= 10:
        return {
            "text": f"Rapid dovish repricing (+{roc_7d:.1f}pts in 7d)",
            "color": GREEN,
            "action": (
                "Momentum trade: TLT, XLF, IWM catching a bid fast. "
                "Watch for gap-ups in rate-sensitive names."
            ),
        }

    if roc_7d is not None and roc_7d <= -10:
        return {
            "text": f"Rapid hawkish repricing ({roc_7d:.1f}pts in 7d)",
            "color": RED,
            "action": (
                "Everything repricing. QQQ most vulnerable. Defensive rotation incoming. "
                "Tighten all stops."
            ),
        }

    if yes_prob >= 70:
        return {
            "text": f"Market pricing cuts ({yes_prob:.0f}% probability)",
            "color": GREEN,
            "action": (
                "Long bias: TLT, XLF, IWM, rate-sensitive names. Growth over value. "
                "Dovish environment confirmed."
            ),
        }
    if yes_prob >= 40:
        return {
            "text": f"Uncertain — market undecided ({yes_prob:.0f}%)",
            "color": YELLOW,
            "action": "No directional edge from rate expectations. Trade technicals not macro. Wait for clarity.",
        }
    return {
        "text": f"Higher for longer being priced ({yes_prob:.0f}%)",
        "color": RED,
        "action": (
            "Short bias rate-sensitive sectors. XLF under pressure. Growth stocks face headwind. "
            "Favor value, energy, defensive."
        ),
    }


def get_recession_implication(yes_prob: float, roc_7d: float) -> dict:
    if yes_prob is None:
        return {
            "text": "Data unavailable",
            "color": MUTED,
            "action": "No actionable signal",
        }

    if roc_7d is not None and roc_7d >= 8:
        return {
            "text": f"Recession fear accelerating (+{roc_7d:.1f}pts in 7d)",
            "color": RED,
            "action": (
                "Reduce size everywhere. Watch HY spreads. If they blow out too, it's confirmed. "
                "IWM shorts over SPY shorts."
            ),
        }

    if yes_prob < 20:
        return {
            "text": f"Low recession risk ({yes_prob:.0f}%)",
            "color": GREEN,
            "action": "Risk-on confirmed by crowd. Momentum setups have structural tailwind. Full size on A+ setups.",
        }
    if yes_prob < 35:
        return {
            "text": f"Elevated concern ({yes_prob:.0f}%)",
            "color": YELLOW,
            "action": "Don't fight momentum but keep stops tighter than usual. Avoid adding to losers.",
        }
    if yes_prob < 50:
        return {
            "text": f"Serious concern ({yes_prob:.0f}%)",
            "color": DK_ORANGE,
            "action": (
                "Short bias cyclicals: XLY, XLI. Defensive rotation makes sense: XLP, XLV, GLD. "
                "Fade gap-ups in discretionary."
            ),
        }
    return {
        "text": f"Majority pricing recession ({yes_prob:.0f}%)",
        "color": RED,
        "action": (
            "Full defensive posture. Fade every rip. IWM shorts over SPY. Beat-and-Sell probability "
            "elevated on all earnings plays."
        ),
    }


def get_btc_correlation_implication(correlation_30d: float) -> dict:
    if correlation_30d is None:
        return {
            "text": "Correlation unavailable",
            "color": MUTED,
            "action": "No signal",
        }

    if correlation_30d >= 0.7:
        return {
            "text": f"High correlation ({correlation_30d:.2f}) — BTC = leveraged SPY",
            "color": YELLOW,
            "action": (
                "No additional info from crypto. BITO is just SPY amplified. Don't use crypto as a separate "
                "signal today."
            ),
        }
    if correlation_30d >= 0.4:
        return {
            "text": f"Moderate correlation ({correlation_30d:.2f})",
            "color": LT_GREEN,
            "action": (
                "BTC partially following its own story. Watch for divergence to develop. COIN and MSTR may have "
                "independent setups forming."
            ),
        }
    return {
        "text": f"Low correlation ({correlation_30d:.2f}) — BTC has its own story",
        "color": GREEN,
        "action": (
            "Crypto-native catalyst active. BTC and equities diverging. COIN, MSTR, BITO may move independently. "
            "Watch for crypto-specific setups."
        ),
    }


def get_fear_greed_implication(value: int) -> dict:
    if value is None:
        return {
            "text": "Data unavailable",
            "color": MUTED,
            "action": "No signal",
        }

    if value <= 25:
        return {
            "text": f"Extreme fear ({value}) — contrarian long setup",
            "color": GREEN,
            "action": (
                "Capitulation happening in crypto. COIN, MSTR, BITO: look for reversal candles on the daily chart. "
                "Mean reversion bias."
            ),
        }
    if value <= 45:
        return {
            "text": f"Fear ({value})",
            "color": YELLOW,
            "action": "Caution dominant in crypto. Don't chase bounces. Wait for F&G to stabilize above 40 before adding crypto exposure.",
        }
    if value <= 55:
        return {
            "text": f"Neutral ({value})",
            "color": MUTED,
            "action": "No sentiment edge. Trade the chart, not the sentiment. No contrarian setup available.",
        }
    if value <= 75:
        return {
            "text": f"Greed ({value}) — momentum mode",
            "color": LT_GREEN,
            "action": "Momentum setups working. Trend-following mode active. Let winners run longer than usual in crypto names.",
        }
    return {
        "text": f"Extreme greed ({value}) — fade setups",
        "color": RED,
        "action": "Crowd is euphoric. Look for shorts on COIN and MSTR on technical weakness. Do not chase crypto longs.",
    }


def get_btc_dominance_implication(dominance: float, dom_roc_20d: float) -> dict:
    if dominance is None:
        return {
            "text": "Data unavailable",
            "color": MUTED,
            "action": "No signal",
        }

    if dominance > 60 and dom_roc_20d is not None and dom_roc_20d > 2:
        return {
            "text": f"BTC dominance rising ({dominance:.1f}%) — flight to crypto safety",
            "color": YELLOW,
            "action": "Risk-off within crypto. Altcoins being crushed. Stick with BTC or BITO over speculative altcoin plays.",
        }
    if dominance < 50 and dom_roc_20d is not None and dom_roc_20d < -2:
        return {
            "text": f"Altcoin season signal ({dominance:.1f}% and falling)",
            "color": GREEN,
            "action": (
                "Capital rotating into alts. Speculative risk appetite surging in crypto. If the composite score is also "
                "recovering, momentum setups have maximum tailwind."
            ),
        }
    if dominance > 55:
        return {
            "text": f"BTC dominant ({dominance:.1f}%) — cautious crypto environment",
            "color": YELLOW,
            "action": "Investors prefer BTC over alts. BITO is safer than speculative crypto-adjacent names.",
        }
    return {
        "text": f"Balanced dominance ({dominance:.1f}%)",
        "color": LT_GREEN,
        "action": "Normal capital distribution. No strong rotation signal. Watch for a dominance direction change as a leading indicator.",
    }


def get_divergence_signal(spy_20d_pct: float, recession_prob: float, fed_cut_prob: float) -> dict:
    """
    Detects when SPY price action contradicts prediction market signals.
    Returns implication dict.
    """
    if spy_20d_pct is None or recession_prob is None:
        return {
            "text": "Insufficient data",
            "color": MUTED,
            "action": "Cannot compute divergence",
        }

    spy_bullish = spy_20d_pct > 2
    spy_bearish = spy_20d_pct < -2
    recession_high = recession_prob > 40
    recession_low = recession_prob < 20
    cuts_likely = fed_cut_prob is not None and fed_cut_prob > 60

    if spy_bullish and recession_high:
        return {
            "text": "Divergence: SPY rallying but recession odds elevated",
            "color": RED,
            "action": (
                "Equity market may be in denial. Smart money is buying protection while price rises. Fade the rally. "
                "Beat-and-Sell setups have higher probability here."
            ),
        }
    if spy_bearish and recession_low:
        return {
            "text": "Divergence: SPY selling but crowd sees no recession",
            "color": GREEN,
            "action": (
                "Equity market may be oversold versus crowd wisdom. Dip-buy candidates are emerging. Look for reversal "
                "setups in quality names."
            ),
        }
    if spy_bearish and cuts_likely:
        return {
            "text": "Divergence: SPY weak but rate cuts incoming",
            "color": YELLOW,
            "action": (
                "Bond market may be leading equities. Rate-sensitive names have not fully priced in the dovish shift. "
                "Long bias could be building."
            ),
        }
    if spy_bullish and not cuts_likely:
        return {
            "text": "Divergence: SPY strong but no rate catalyst",
            "color": YELLOW,
            "action": "Rally built on no macro support. Tighter stops on all longs. Do not add size to this rally.",
        }
    return {
        "text": "No divergence — signals aligned",
        "color": GREEN,
        "action": "Price action and prediction markets are telling the same story. Higher conviction environment.",
    }


def _fallback_chart(message: str, height: int = 280) -> str:
    fig = go.Figure()
    fig.add_annotation(
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        text=message,
        showarrow=False,
        font=dict(color=MUTED, size=14),
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        height=height,
        margin=dict(l=30, r=30, t=30, b=30),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)


def build_fed_cut_panel(fed_data: dict, spy_series: pd.Series) -> str:
    yes_prob = fed_data.get("current_yes_prob")
    history = _sanitize_index(fed_data.get("history", _empty_series()))
    roc_7d = None
    if len(history) >= 8:
        roc_7d = float(history.iloc[-1] - history.iloc[-8])

    impl = get_fed_cut_implication(yes_prob, roc_7d)

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.7, 0.3],
        subplot_titles=[
            "Fed Rate Cut Probability — 90 Day History",
            "7-Day Rate of Change (percentage points)",
        ],
        specs=[[{"secondary_y": True}], [{"secondary_y": False}]],
    )

    if not history.empty:
        fig.add_trace(
            go.Scatter(
                x=history.index,
                y=history.values,
                name="Cut Probability %",
                line=dict(color=GREEN, width=2.5),
                fill="tozeroy",
                fillcolor="rgba(38,166,154,0.1)",
                hovertemplate="%{x|%Y-%m-%d}<br>Probability: %{y:.1f}%<extra></extra>",
            ),
            row=1,
            col=1,
            secondary_y=False,
        )
        fig.add_hline(y=50, line_dash="dash", line_color=MUTED, line_width=1, row=1, col=1)

        if spy_series is not None and not spy_series.empty:
            aligned_spy = _sanitize_index(spy_series)
            common_start = max(history.index[0], aligned_spy.index[0])
            spy_aligned = aligned_spy[aligned_spy.index >= common_start]
            fig.add_trace(
                go.Scatter(
                    x=spy_aligned.index,
                    y=spy_aligned.values,
                    name="SPY Price",
                    line=dict(color=BLUE, width=1.5, dash="dot"),
                    hovertemplate="SPY: $%{y:.2f}<extra></extra>",
                ),
                row=1,
                col=1,
                secondary_y=True,
            )

        roc_series = history.diff(7).dropna()
        fig.add_trace(
            go.Bar(
                x=roc_series.index,
                y=roc_series.values,
                marker_color=[GREEN if value >= 0 else RED for value in roc_series.values],
                name="7d ROC",
                showlegend=False,
                hovertemplate="%{x|%Y-%m-%d}<br>ROC: %{y:+.1f}pts<extra></extra>",
            ),
            row=2,
            col=1,
        )
        fig.add_hline(y=0, line_color=MUTED, line_width=1, row=2, col=1)
    else:
        fig.add_annotation(
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            text="Polymarket Fed history unavailable",
            showarrow=False,
            font=dict(color=MUTED, size=14),
        )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        height=450,
        margin=dict(l=60, r=60, t=50, b=30),
        legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center", font=dict(color=TEXT)),
        yaxis=dict(title="Cut Probability %", gridcolor=BORDER, range=[0, 100]),
        yaxis2=dict(title="SPY Price ($)", gridcolor=BORDER, showgrid=False),
        yaxis3=dict(title="ROC (pts)", gridcolor=BORDER),
        xaxis2=dict(gridcolor=BORDER),
    )

    prob_display = f"{yes_prob:.1f}%" if yes_prob is not None else "N/A"
    roc_display = f"{roc_7d:+.1f}pts" if roc_7d is not None else "N/A"
    chart_html = fig.to_html(full_html=False, include_plotlyjs=False)

    return f"""
    <div class="panel-section">
      <div class="big-stat-row">
        <div class="big-stat-card" style="border-color:{impl['color']};">
          <div class="big-stat-label">AT LEAST 1 CUT IN 2026</div>
          <div class="big-stat-value" style="color:{impl['color']};">{prob_display}</div>
          <div class="big-stat-sub">Current Market Probability</div>
        </div>
        <div class="big-stat-card" style="border-color:{BLUE};">
          <div class="big-stat-label">7-DAY CHANGE</div>
          <div class="big-stat-value" style="color:{BLUE}; font-size:32px;">{roc_display}</div>
          <div class="big-stat-sub">Rate of Change</div>
        </div>
        <div class="implication-card" style="border-color:{impl['color']}; background:{impl['color']}11;">
          <div class="impl-signal" style="color:{impl['color']};">{impl['text']}</div>
          <div class="impl-action">{impl['action']}</div>
        </div>
      </div>
      {chart_html}
    </div>
    """


def build_recession_panel(rec_data: dict, spy_series: pd.Series) -> str:
    yes_prob = rec_data.get("current_yes_prob")
    history = _sanitize_index(rec_data.get("history", _empty_series()))
    roc_7d = None
    if len(history) >= 8:
        roc_7d = float(history.iloc[-1] - history.iloc[-8])

    impl = get_recession_implication(yes_prob, roc_7d)
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.7, 0.3],
        subplot_titles=[
            "US Recession Probability — 90 Day History",
            "7-Day Rate of Change (percentage points)",
        ],
        specs=[[{"secondary_y": True}], [{"secondary_y": False}]],
    )

    if not history.empty:
        line_color = RED if (yes_prob or 0) > 40 else YELLOW if (yes_prob or 0) > 20 else GREEN
        fig.add_trace(
            go.Scatter(
                x=history.index,
                y=history.values,
                name="Recession Probability %",
                line=dict(color=line_color, width=2.5),
                fill="tozeroy",
                fillcolor="rgba(239,83,80,0.1)",
                hovertemplate="%{x|%Y-%m-%d}<br>Probability: %{y:.1f}%<extra></extra>",
            ),
            row=1,
            col=1,
            secondary_y=False,
        )
        fig.add_hrect(y0=40, y1=100, fillcolor="rgba(239,83,80,0.05)", line_width=0, row=1, col=1)
        fig.add_hline(y=40, line_dash="dash", line_color=RED, line_width=1, annotation_text="Danger Zone", annotation_font_color=RED, row=1, col=1)
        fig.add_hline(y=20, line_dash="dash", line_color=YELLOW, line_width=1, annotation_text="Elevated Concern", annotation_font_color=YELLOW, row=1, col=1)

        if spy_series is not None and not spy_series.empty:
            aligned_spy = _sanitize_index(spy_series)
            common_start = max(history.index[0], aligned_spy.index[0])
            spy_aligned = aligned_spy[aligned_spy.index >= common_start]
            fig.add_trace(
                go.Scatter(
                    x=spy_aligned.index,
                    y=spy_aligned.values,
                    name="SPY Price",
                    line=dict(color=BLUE, width=1.5, dash="dot"),
                    hovertemplate="SPY: $%{y:.2f}<extra></extra>",
                ),
                row=1,
                col=1,
                secondary_y=True,
            )

        roc_series = history.diff(7).dropna()
        fig.add_trace(
            go.Bar(
                x=roc_series.index,
                y=roc_series.values,
                marker_color=[RED if value >= 0 else GREEN for value in roc_series.values],
                name="7d ROC",
                showlegend=False,
                hovertemplate="%{x|%Y-%m-%d}<br>ROC: %{y:+.1f}pts<extra></extra>",
            ),
            row=2,
            col=1,
        )
        fig.add_hline(y=0, line_color=MUTED, line_width=1, row=2, col=1)
    else:
        fig.add_annotation(
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            text="Polymarket recession history unavailable",
            showarrow=False,
            font=dict(color=MUTED, size=14),
        )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        height=450,
        margin=dict(l=60, r=60, t=50, b=30),
        legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center", font=dict(color=TEXT)),
        yaxis=dict(title="Recession Probability %", gridcolor=BORDER, range=[0, 100]),
        yaxis2=dict(title="SPY Price ($)", showgrid=False),
        xaxis2=dict(gridcolor=BORDER),
    )

    prob_display = f"{yes_prob:.1f}%" if yes_prob is not None else "N/A"
    roc_display = f"{roc_7d:+.1f}pts" if roc_7d is not None else "N/A"
    roc_color = RED if (roc_7d or 0) > 0 else GREEN
    chart_html = fig.to_html(full_html=False, include_plotlyjs=False)

    return f"""
    <div class="panel-section">
      <div class="big-stat-row">
        <div class="big-stat-card" style="border-color:{impl['color']};">
          <div class="big-stat-label">US RECESSION BY END OF 2026</div>
          <div class="big-stat-value" style="color:{impl['color']};">{prob_display}</div>
          <div class="big-stat-sub">Market-Implied Probability</div>
        </div>
        <div class="big-stat-card" style="border-color:{roc_color};">
          <div class="big-stat-label">7-DAY CHANGE</div>
          <div class="big-stat-value" style="color:{roc_color}; font-size:32px;">{roc_display}</div>
          <div class="big-stat-sub">Rising = More Fear</div>
        </div>
        <div class="implication-card" style="border-color:{impl['color']}; background:{impl['color']}11;">
          <div class="impl-signal" style="color:{impl['color']};">{impl['text']}</div>
          <div class="impl-action">{impl['action']}</div>
        </div>
      </div>
      {chart_html}
    </div>
    """


def build_btc_panel(btc_data: dict, dom_data: dict) -> str:
    bito = _sanitize_index(btc_data.get("bito", _empty_series()))
    spy = _sanitize_index(btc_data.get("spy", _empty_series()))

    corr_30d = None
    corr_series = _empty_series()
    if not bito.empty and not spy.empty and len(bito) >= 30:
        combined = pd.DataFrame({"bito": bito, "spy": spy}).dropna()
        if len(combined) >= 30:
            corr_series = combined["bito"].rolling(30).corr(combined["spy"]).dropna()
            if not corr_series.empty:
                corr_30d = float(corr_series.iloc[-1])

    btc_impl = get_btc_correlation_implication(corr_30d)

    dom_current = dom_data.get("current")
    dom_history = _sanitize_index(dom_data.get("history", _empty_series()))
    dom_roc_20d = None

    # CoinGecko public endpoint above gives BTC price history, not true dominance history.
    # Use it only as a rendering fallback, never as a dominance momentum signal.
    if not dom_history.empty and dom_history.max() <= 100 and len(dom_history) >= 20:
        dom_roc_20d = float(dom_history.iloc[-1] - dom_history.iloc[-20])

    dom_impl = get_btc_dominance_implication(dom_current, dom_roc_20d)

    fig_a = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.6, 0.4],
        subplot_titles=["BITO (Bitcoin ETF) Price", "30-Day Rolling Correlation with SPY"],
    )

    if not bito.empty:
        fig_a.add_trace(
            go.Scatter(
                x=bito.index,
                y=bito.values,
                name="BITO",
                line=dict(color=GOLD, width=2),
                hovertemplate="BITO: $%{y:.2f}<extra></extra>",
            ),
            row=1,
            col=1,
        )
    else:
        fig_a.add_annotation(x=0.5, y=0.8, xref="paper", yref="paper", text="BITO price unavailable", showarrow=False, font=dict(color=MUTED, size=14))

    if not corr_series.empty:
        fig_a.add_trace(
            go.Scatter(
                x=corr_series.index,
                y=corr_series.values,
                name="30d Correlation",
                line=dict(color=BLUE, width=2),
                fill="tozeroy",
                fillcolor="rgba(66,165,245,0.1)",
                hovertemplate="%{x|%Y-%m-%d}<br>Correlation: %{y:.3f}<extra></extra>",
            ),
            row=2,
            col=1,
        )
        for level, color, label in [(0.7, RED, "High (BTC=SPY proxy)"), (0.3, GREEN, "Low (BTC independent)")]:
            fig_a.add_hline(y=level, line_dash="dash", line_color=color, line_width=1, annotation_text=label, annotation_font_color=color, row=2, col=1)
    else:
        fig_a.add_annotation(x=0.5, y=0.2, xref="paper", yref="paper", text="Correlation unavailable", showarrow=False, font=dict(color=MUTED, size=14))

    fig_a.update_layout(
        template="plotly_dark",
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        height=420,
        margin=dict(l=60, r=30, t=50, b=30),
        yaxis=dict(title="BITO Price ($)", gridcolor=BORDER),
        yaxis2=dict(title="Correlation", gridcolor=BORDER, range=[-1, 1]),
        xaxis2=dict(gridcolor=BORDER),
    )

    fig_b = go.Figure()
    if dom_current is not None:
        fig_b.add_trace(
            go.Indicator(
                mode="gauge+number+delta",
                value=dom_current,
                title={"text": "Bitcoin Dominance %", "font": {"color": TEXT}},
                delta={"reference": 50, "valueformat": ".1f", "suffix": "%"},
                gauge={
                    "axis": {"range": [0, 100], "tickcolor": MUTED},
                    "bar": {"color": GOLD},
                    "bgcolor": CARD_BG,
                    "bordercolor": BORDER,
                    "steps": [
                        {"range": [0, 40], "color": "rgba(38,166,154,0.2)"},
                        {"range": [40, 60], "color": "rgba(255,167,38,0.2)"},
                        {"range": [60, 100], "color": "rgba(239,83,80,0.2)"},
                    ],
                    "threshold": {
                        "line": {"color": "white", "width": 3},
                        "thickness": 0.75,
                        "value": 50,
                    },
                },
            )
        )
    else:
        fig_b.add_annotation(x=0.5, y=0.5, xref="paper", yref="paper", text="BTC dominance unavailable", showarrow=False, font=dict(color=MUTED, size=14))

    fig_b.update_layout(
        template="plotly_dark",
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        height=280,
        margin=dict(l=30, r=30, t=30, b=30),
        font=dict(color=TEXT),
    )

    chart_a_html = fig_a.to_html(full_html=False, include_plotlyjs=False)
    chart_b_html = fig_b.to_html(full_html=False, include_plotlyjs=False)
    corr_display = f"{corr_30d:.2f}" if corr_30d is not None else "N/A"
    dom_display = f"{dom_current:.1f}%" if dom_current is not None else "N/A"

    return f"""
    <div class="panel-section">
      <div class="big-stat-row">
        <div class="big-stat-card" style="border-color:{btc_impl['color']};">
          <div class="big-stat-label">BTC/SPY 30D CORRELATION</div>
          <div class="big-stat-value" style="color:{btc_impl['color']};">{corr_display}</div>
          <div class="big-stat-sub">1.0 = Perfect lockstep</div>
        </div>
        <div class="big-stat-card" style="border-color:{GOLD};">
          <div class="big-stat-label">BTC DOMINANCE</div>
          <div class="big-stat-value" style="color:{GOLD};">{dom_display}</div>
          <div class="big-stat-sub">BTC share of total crypto</div>
        </div>
        <div class="implication-card" style="border-color:{btc_impl['color']}; background:{btc_impl['color']}11;">
          <div class="impl-signal" style="color:{btc_impl['color']};">{btc_impl['text']}</div>
          <div class="impl-action">{btc_impl['action']}</div>
        </div>
      </div>
      {chart_a_html}
      <div class="two-col-row">
        <div class="col-left">{chart_b_html}</div>
        <div class="col-right">
          <div class="implication-card tall" style="border-color:{dom_impl['color']}; background:{dom_impl['color']}11;">
            <div class="impl-label">BTC DOMINANCE SIGNAL</div>
            <div class="impl-signal" style="color:{dom_impl['color']};">{dom_impl['text']}</div>
            <div class="impl-action">{dom_impl['action']}</div>
          </div>
        </div>
      </div>
    </div>
    """


def build_fear_greed_panel(fg_data: dict) -> str:
    value = fg_data.get("current_value")
    classification = fg_data.get("classification", "")
    history = _sanitize_index(fg_data.get("history", _empty_series()))
    impl = get_fear_greed_implication(value)

    fig_gauge = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value if value is not None else 0,
            title={"text": f"Crypto Fear & Greed — {classification}", "font": {"color": TEXT, "size": 16}},
            gauge={
                "axis": {
                    "range": [0, 100],
                    "tickvals": [0, 25, 45, 55, 75, 100],
                    "ticktext": ["0", "Extreme<br>Fear", "Fear", "Neutral", "Greed", "Extreme<br>Greed"],
                    "tickcolor": MUTED,
                },
                "bar": {"color": impl["color"]},
                "bgcolor": CARD_BG,
                "bordercolor": BORDER,
                "steps": [
                    {"range": [0, 25], "color": "rgba(38,166,154,0.25)"},
                    {"range": [25, 45], "color": "rgba(255,167,38,0.15)"},
                    {"range": [45, 55], "color": "rgba(136,136,136,0.15)"},
                    {"range": [55, 75], "color": "rgba(102,187,106,0.15)"},
                    {"range": [75, 100], "color": "rgba(239,83,80,0.25)"},
                ],
            },
        )
    )
    fig_gauge.update_layout(template="plotly_dark", paper_bgcolor=BG, plot_bgcolor=BG, height=280, margin=dict(l=30, r=30, t=50, b=20), font=dict(color=TEXT))

    fig_hist = go.Figure()
    if not history.empty:
        fig_hist.add_trace(
            go.Scatter(
                x=history.index,
                y=history.values,
                mode="lines",
                name="Fear & Greed",
                line=dict(color=BLUE, width=2),
                fill="tozeroy",
                fillcolor="rgba(66,165,245,0.08)",
                hovertemplate="%{x|%Y-%m-%d}<br>F&G Index: %{y:.0f}<extra></extra>",
            )
        )
        for y0, y1, color in [(0, 25, "rgba(38,166,154,0.08)"), (75, 100, "rgba(239,83,80,0.08)")]:
            fig_hist.add_hrect(y0=y0, y1=y1, fillcolor=color, line_width=0)
        for level, color, label in [(25, GREEN, "Extreme Fear"), (75, RED, "Extreme Greed"), (50, MUTED, "Neutral")]:
            fig_hist.add_hline(y=level, line_dash="dash", line_color=color, line_width=1, annotation_text=label, annotation_font_color=color, annotation_position="right")
    else:
        fig_hist.add_annotation(x=0.5, y=0.5, xref="paper", yref="paper", text="Fear & Greed history unavailable", showarrow=False, font=dict(color=MUTED, size=14))

    fig_hist.update_layout(
        template="plotly_dark",
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        height=280,
        margin=dict(l=60, r=80, t=30, b=30),
        title=dict(text="90-Day Fear & Greed History", font=dict(color=TEXT, size=14)),
        yaxis=dict(title="Index Value", gridcolor=BORDER, range=[0, 100]),
        xaxis=dict(gridcolor=BORDER),
    )

    gauge_html = fig_gauge.to_html(full_html=False, include_plotlyjs=False)
    hist_html = fig_hist.to_html(full_html=False, include_plotlyjs=False)

    return f"""
    <div class="panel-section">
      <div class="two-col-row">
        <div class="col-left">{gauge_html}</div>
        <div class="col-right">{hist_html}</div>
      </div>
      <div class="implication-card wide" style="border-color:{impl['color']}; background:{impl['color']}11; margin-top:12px;">
        <div class="impl-signal" style="color:{impl['color']}; font-size:15px;">{impl['text']}</div>
        <div class="impl-action">{impl['action']}</div>
      </div>
    </div>
    """


def build_verdict_panel(fed_data: dict, rec_data: dict, btc_data: dict, fg_data: dict, dom_data: dict) -> str:
    fed_prob = fed_data.get("current_yes_prob")
    rec_prob = rec_data.get("current_yes_prob")
    fg_value = fg_data.get("current_value")

    bito = _sanitize_index(btc_data.get("bito", _empty_series()))
    spy = _sanitize_index(btc_data.get("spy", _empty_series()))

    spy_20d_pct = None
    if not spy.empty and len(spy) >= 20:
        spy_20d_pct = float(spy.iloc[-1] - spy.iloc[-20]) / float(spy.iloc[-20]) * 100

    corr = None
    if not bito.empty and not spy.empty:
        combined = pd.DataFrame({"bito": bito, "spy": spy}).dropna()
        if len(combined) >= 30:
            corr = float(combined["bito"].tail(30).corr(combined["spy"].tail(30)))

    div_signal = get_divergence_signal(spy_20d_pct, rec_prob, fed_prob)
    signals = []

    if fed_prob is not None:
        fed_impl = get_fed_cut_implication(fed_prob, None)
        signals.append({
            "name": "Fed Rate Cuts",
            "reading": f"{fed_prob:.0f}% probability",
            "signal": fed_impl["text"],
            "color": fed_impl["color"],
            "action": fed_impl["action"],
        })

    if rec_prob is not None:
        rec_impl = get_recession_implication(rec_prob, None)
        signals.append({
            "name": "Recession Risk",
            "reading": f"{rec_prob:.0f}% probability",
            "signal": rec_impl["text"],
            "color": rec_impl["color"],
            "action": rec_impl["action"],
        })

    if corr is not None:
        btc_impl = get_btc_correlation_implication(corr)
        signals.append({
            "name": "BTC/SPY Correlation",
            "reading": f"{corr:.2f}",
            "signal": btc_impl["text"],
            "color": btc_impl["color"],
            "action": btc_impl["action"],
        })

    if fg_value is not None:
        fg_impl = get_fear_greed_implication(fg_value)
        signals.append({
            "name": "Crypto Fear & Greed",
            "reading": f"{fg_value}/100",
            "signal": fg_impl["text"],
            "color": fg_impl["color"],
            "action": fg_impl["action"],
        })

    if dom_data.get("current") is not None:
        dom_impl = get_btc_dominance_implication(dom_data.get("current"), None)
        signals.append({
            "name": "BTC Dominance",
            "reading": f"{dom_data['current']:.1f}%",
            "signal": dom_impl["text"],
            "color": dom_impl["color"],
            "action": dom_impl["action"],
        })

    bullish = sum(1 for signal in signals if signal["color"] in [GREEN, LT_GREEN])
    bearish = sum(1 for signal in signals if signal["color"] in [RED, DK_ORANGE])
    total = len(signals)

    if total == 0:
        overall_color = MUTED
        overall_label = "INSUFFICIENT DATA"
        overall_sub = "Check data connections."
    elif bullish >= total * 0.75:
        overall_color = GREEN
        overall_label = "BROADLY BULLISH"
        overall_sub = "Most signals aligned risk-on. High conviction environment. Trust your long setups."
    elif bearish >= total * 0.75:
        overall_color = RED
        overall_label = "BROADLY BEARISH"
        overall_sub = "Most signals aligned risk-off. Short bias. Fade rallies. Reduce size on longs."
    elif bullish > bearish:
        overall_color = LT_GREEN
        overall_label = "CAUTIOUSLY BULLISH"
        overall_sub = "More green than red. Long bias but stay selective. Only A+ setups at full size."
    elif bearish > bullish:
        overall_color = YELLOW
        overall_label = "CAUTIOUSLY BEARISH"
        overall_sub = "More red than green. Reduce long exposure. Short setups getting better."
    else:
        overall_color = MUTED
        overall_label = "MIXED SIGNALS"
        overall_sub = "No clear directional edge. Trade smaller. Wait for signals to align."

    signal_rows = ""
    for signal in signals:
        color = signal["color"]
        signal_rows += f"""
        <div class="verdict-row">
          <div class="verdict-name">{signal['name']}</div>
          <div class="verdict-reading" style="color:{color};">{signal['reading']}</div>
          <div class="verdict-signal" style="color:{color};">{signal['signal']}</div>
          <div class="verdict-action">{signal['action']}</div>
        </div>
        """

    return f"""
    <div class="panel-section verdict-panel">
      <div class="overall-verdict" style="border-color:{overall_color}; background:{overall_color}18;">
        <div class="overall-label" style="color:{overall_color};">DASHBOARD VERDICT: {overall_label}</div>
        <div class="overall-sub">{overall_sub}</div>
        <div class="signal-count">{bullish} bullish · {bearish} bearish · {total - bullish - bearish} neutral out of {total} signals</div>
      </div>

      <div class="divergence-box" style="border-color:{div_signal['color']}; background:{div_signal['color']}11; margin:16px 0;">
        <div class="div-label">SPY vs PREDICTION MARKETS</div>
        <div class="div-signal" style="color:{div_signal['color']};">{div_signal['text']}</div>
        <div class="div-action">{div_signal['action']}</div>
      </div>

      <div class="signal-table">
        <div class="signal-table-header">
          <span>SIGNAL</span>
          <span>READING</span>
          <span>STATUS</span>
          <span>ACTIONABLE INSIGHT</span>
        </div>
        {signal_rows}
      </div>
    </div>
    """


GLOBAL_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  background: #111111;
  color: #e0e0e0;
  font-family: 'Segoe UI', system-ui, sans-serif;
}
.dash-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px 12px;
  border-bottom: 1px solid #2a2a2a;
}
.dash-header h1 {
  font-size: 22px;
  font-weight: 700;
  color: #e0e0e0;
  letter-spacing: 0.5px;
}
.dash-subtitle {
  font-size: 11px;
  color: #888888;
  margin-top: 2px;
}
.dash-ts {
  font-size: 12px;
  color: #888888;
}
.panel-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 3px;
  color: #888888;
  text-transform: uppercase;
  padding: 18px 24px 4px;
  border-left: 3px solid;
  margin: 8px 0 0 0;
}
.panel-section {
  padding: 12px 24px 20px;
  border-bottom: 1px solid #2a2a2a;
}
.big-stat-row {
  display: grid;
  grid-template-columns: 1fr 1fr 2fr;
  gap: 16px;
  margin-bottom: 16px;
}
.big-stat-card {
  background: #1a1a1a;
  border: 1px solid;
  border-radius: 6px;
  padding: 16px 20px;
  text-align: center;
}
.big-stat-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.5px;
  color: #888888;
  text-transform: uppercase;
  margin-bottom: 8px;
}
.big-stat-value {
  font-size: 44px;
  font-weight: 700;
  letter-spacing: -1px;
  line-height: 1.1;
}
.big-stat-sub {
  font-size: 11px;
  color: #888888;
  margin-top: 4px;
}
.implication-card {
  background: #1a1a1a;
  border: 1px solid;
  border-radius: 6px;
  padding: 16px 20px;
}
.implication-card.wide {
  width: 100%;
}
.implication-card.tall {
  height: 100%;
  min-height: 200px;
}
.impl-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.5px;
  color: #888888;
  text-transform: uppercase;
  margin-bottom: 8px;
}
.impl-signal {
  font-size: 15px;
  font-weight: 700;
  margin-bottom: 10px;
  line-height: 1.4;
}
.impl-action {
  font-size: 12px;
  color: #cccccc;
  line-height: 1.6;
}
.two-col-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 12px;
}
.col-left, .col-right {
  min-width: 0;
}
.verdict-panel {
  background: #0d0d0d;
}
.overall-verdict {
  border: 2px solid;
  border-radius: 8px;
  padding: 20px 24px;
  text-align: center;
  margin-bottom: 16px;
}
.overall-label {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: 1px;
  margin-bottom: 8px;
}
.overall-sub {
  font-size: 14px;
  color: #cccccc;
  margin-bottom: 8px;
  line-height: 1.5;
}
.signal-count {
  font-size: 12px;
  color: #888888;
}
.divergence-box {
  border: 1px solid;
  border-radius: 6px;
  padding: 14px 20px;
}
.div-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.5px;
  color: #888888;
  text-transform: uppercase;
  margin-bottom: 6px;
}
.div-signal {
  font-size: 15px;
  font-weight: 700;
  margin-bottom: 6px;
}
.div-action {
  font-size: 12px;
  color: #cccccc;
  line-height: 1.5;
}
.signal-table {
  border: 1px solid #2a2a2a;
  border-radius: 6px;
  overflow: hidden;
}
.signal-table-header {
  display: grid;
  grid-template-columns: 1fr 1fr 2fr 3fr;
  gap: 12px;
  padding: 10px 16px;
  background: #1a1a1a;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.5px;
  color: #888888;
  text-transform: uppercase;
}
.verdict-row {
  display: grid;
  grid-template-columns: 1fr 1fr 2fr 3fr;
  gap: 12px;
  padding: 12px 16px;
  border-top: 1px solid #2a2a2a;
  font-size: 12px;
  line-height: 1.5;
}
.verdict-name {
  font-weight: 700;
  color: #e0e0e0;
}
.verdict-reading {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.verdict-signal {
  font-weight: 600;
}
.verdict-action {
  color: #cccccc;
}
@media (max-width: 1100px) {
  .big-stat-row,
  .two-col-row,
  .signal-table-header,
  .verdict-row {
    grid-template-columns: 1fr;
  }
  .dash-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
}
"""


def main():
    print("=" * 55)
    print("  QuantLab Dashboard #2 — PM + Crypto")
    print("=" * 55)

    print("\n[1/5] Fetching Fed rate cut odds...")
    fed_raw = fetch_polymarket_market("616902")
    fed_data = dict(fed_raw)
    if fed_raw.get("current_yes_prob") is not None:
        fed_data["current_yes_prob"] = 100 - fed_raw["current_yes_prob"]
        fed_data["current_no_prob"] = fed_raw["current_yes_prob"]
        if not fed_raw.get("history", _empty_series()).empty:
            fed_data["history"] = 100 - fed_raw["history"]
        print(f"  Cut probability: {fed_data['current_yes_prob']:.1f}%")
    else:
        print(f"  Warning: {fed_raw.get('error', 'No data')}")

    print("[2/5] Fetching recession odds...")
    rec_data = fetch_polymarket_market("609655")
    if rec_data.get("current_yes_prob") is not None:
        print(f"  Recession probability: {rec_data['current_yes_prob']:.1f}%")
    else:
        print(f"  Warning: {rec_data.get('error', 'No data')}")

    print("[3/5] Fetching BTC + SPY prices...")
    btc_data = fetch_btc_spy_data()
    if not btc_data["bito"].empty:
        print(f"  BITO: {len(btc_data['bito'])} days loaded")
    else:
        print(f"  Warning: {btc_data.get('error', 'No data')}")

    print("[4/5] Fetching Crypto Fear & Greed...")
    fg_data = fetch_fear_greed()
    if fg_data.get("current_value") is not None:
        print(f"  F&G: {fg_data['current_value']} ({fg_data['classification']})")
    else:
        print(f"  Warning: {fg_data.get('error', 'No data')}")

    print("[5/5] Fetching BTC Dominance...")
    dom_data = fetch_btc_dominance()
    if dom_data.get("current") is not None:
        print(f"  BTC Dominance: {dom_data['current']:.1f}%")
    else:
        print(f"  Warning: {dom_data.get('error', 'No data')}")

    print("\nBuilding panels...")
    spy_series = btc_data.get("spy", _empty_series())
    panel1 = build_fed_cut_panel(fed_data, spy_series)
    panel2 = build_recession_panel(rec_data, spy_series)
    panel3 = build_btc_panel(btc_data, dom_data)
    panel4 = build_fear_greed_panel(fg_data)
    panel5 = build_verdict_panel(fed_data, rec_data, btc_data, fg_data, dom_data)

    panel_configs = [
        ("1", "FED RATE CUT ODDS", GREEN, panel1),
        ("2", "RECESSION PROBABILITY", RED, panel2),
        ("3", "BITCOIN AS MACRO SIGNAL", GOLD, panel3),
        ("4", "CRYPTO FEAR & GREED INDEX", PURPLE, panel4),
        ("5", "COMBINED VERDICT + DIVERGENCE", BLUE, panel5),
    ]

    panels_html = ""
    for num, label, color, content in panel_configs:
        panels_html += f"""
        <div class="panel-label" style="border-color:{color}; color:{color};">
          PANEL {num} — {label}
        </div>
        {content}
        """

    ct = datetime.now(ZoneInfo("America/Chicago"))
    ts = ct.strftime("%Y-%m-%d  %H:%M CT")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>QuantLab Dashboard #2</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>{GLOBAL_CSS}</style>
</head>
<body>
  <div class="dash-header">
    <div>
      <h1>QuantLab Dashboard #2</h1>
      <div class="dash-subtitle">Prediction Markets · Bitcoin · Crypto Sentiment</div>
    </div>
    <div class="dash-ts">Last Updated: {ts}</div>
  </div>
  {panels_html}
</body>
</html>"""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    size_kb = OUTPUT_FILE.stat().st_size / 1024

    print(f"\n{'=' * 55}")
    print("  Dashboard #2 Complete")
    print(f"{'=' * 55}")
    print(f"  Fed Cut Probability: {fed_data.get('current_yes_prob', 'N/A')}")
    print(f"  Recession Odds:      {rec_data.get('current_yes_prob', 'N/A')}")
    print(f"  Crypto F&G:          {fg_data.get('current_value', 'N/A')} ({fg_data.get('classification', '')})")
    print(f"  BTC Dominance:       {dom_data.get('current', 'N/A')}")
    print(f"  Output: {OUTPUT_FILE}")
    print(f"  Size:   {size_kb:.0f} KB")
    print(f"{'=' * 55}")


if __name__ == "__main__":
    main()