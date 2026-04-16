import sys, os
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

from dotenv import load_dotenv
load_dotenv(r'C:\QuantLab\Data_Lab\.env', override=True)

import re
import math
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import requests
import yfinance as yf
from bs4 import BeautifulSoup
from plotly.subplots import make_subplots

from shared.config.api_clients import FMPClient
from shared.config.env_loader import load_keys
from shared.data_router import DataRouter


GREEN = "#26a69a"
LT_GREEN = "#66bb6a"
YELLOW = "#ffa726"
DK_ORANGE = "#ef6c00"
RED = "#ef5350"
BLUE = "#42a5f5"
PURPLE = "#ab47bc"
GOLD = "#ffd54f"
BRONZE = "#8d6e63"
BG = "#0d1117"
CARD_BG = "#161b22"
TEXT = "#e6edf3"
MUTED = "#8b949e"
BORDER = "#30363d"

TICKER_LABELS = {
    "RKLB": "Rocket Lab",
    "LUNR": "Intuitive Machines",
    "RDW": "Redwire",
    "ASTS": "AST SpaceMobile",
    "PL": "Planet Labs",
    "LMT": "Lockheed Martin",
    "NOC": "Northrop Grumman",
    "RTX": "RTX",
    "GD": "General Dynamics",
    "LHX": "L3Harris",
    "UFO": "Procure Space ETF",
    "MU": "Micron",
    "SNDK": "Sandisk",
    "WDC": "Western Digital",
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "META": "Meta",
    "AMZN": "Amazon",
    "GOOGL": "Alphabet",
    "NVDA": "NVIDIA",
    "TSLA": "Tesla",
    "VRT": "Vertiv",
    "ANET": "Arista",
    "SMCI": "Super Micro",
    "DELL": "Dell",
    "EQIX": "Equinix",
    "AMAT": "Applied Materials",
    "LRCX": "Lam Research",
    "KLAC": "KLA",
    "ASML": "ASML",
    "TER": "Teradyne",
    "TSM": "TSMC ADR",
}

OUTPUT_DIR = Path(r"C:\QuantLab\Data_Lab\studies\theme_signals_dashboard\outputs")
OUTPUT_FILE = OUTPUT_DIR / "index.html"

PLOTLY_LAYOUT = dict(
    paper_bgcolor=BG,
    plot_bgcolor=BG,
    font=dict(color=TEXT, family="Segoe UI, Arial, sans-serif", size=12),
    margin=dict(l=48, r=28, t=48, b=42),
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)

TSMC_OFFICIAL_MONTHLY_FALLBACK = {
    2024: {
        1: (215785, 7.9),
        2: (181648, 11.3),
        3: (195211, 34.3),
        4: (236021, 59.6),
        5: (229620, 30.1),
        6: (207869, 32.9),
        7: (256953, 44.7),
        8: (250866, 33.0),
        9: (251873, 39.6),
        10: (314240, 29.2),
        11: (276058, 34.0),
        12: (278163, 57.8),
    },
    2025: {
        1: (293288, 35.9),
        2: (260009, 43.1),
        3: (285957, 46.5),
        4: (349567, 48.1),
        5: (320516, 39.6),
        6: (263709, 26.9),
        7: (323166, 25.8),
        8: (335772, 33.8),
        9: (330980, 31.4),
        10: (367473, 16.9),
        11: (343614, 24.5),
        12: (335003, 20.4),
    },
    2026: {
        1: (401255, 36.8),
        2: (317657, 22.2),
        3: (415191, 45.2),
    },
}


def _empty_series() -> pd.Series:
    return pd.Series(dtype=float)


def _clean_series(series: pd.Series) -> pd.Series:
    if series is None or series.empty:
        return _empty_series()
    cleaned = pd.to_numeric(series, errors="coerce").dropna().copy()
    cleaned.index = pd.to_datetime(cleaned.index)
    if getattr(cleaned.index, "tz", None) is not None:
        cleaned.index = cleaned.index.tz_localize(None)
    return cleaned.sort_index()


def _normalize_to_100(series: pd.Series) -> pd.Series:
    cleaned = _clean_series(series)
    if cleaned.empty:
        return cleaned
    return cleaned / cleaned.iloc[0] * 100.0


def _pct_change(series: pd.Series, periods: int) -> float | None:
    cleaned = _clean_series(series)
    if len(cleaned) <= periods:
        return None
    base = cleaned.iloc[-periods - 1]
    latest = cleaned.iloc[-1]
    if pd.isna(base) or base == 0:
        return None
    return (latest / base - 1) * 100.0


def _ytd_change(series: pd.Series) -> float | None:
    cleaned = _clean_series(series)
    if cleaned.empty:
        return None
    current_year = cleaned.index.max().year
    ytd = cleaned[cleaned.index.year == current_year]
    if len(ytd) < 2:
        return None
    base = ytd.iloc[0]
    latest = ytd.iloc[-1]
    if base == 0:
        return None
    return (latest / base - 1) * 100.0


def _fmt_pct(value: float | None) -> str:
    return "N/A" if value is None else f"{value:+.1f}%"


def _latest_value(series: pd.Series) -> float | None:
    cleaned = _clean_series(series)
    if cleaned.empty:
        return None
    return float(cleaned.iloc[-1])


def _quarter_label(idx) -> str:
    ts = pd.Timestamp(idx)
    quarter = ((ts.month - 1) // 3) + 1
    return f"{ts.year}Q{quarter}"


def _safe_divide(a: float | None, b: float | None) -> float | None:
    if a is None or b in (None, 0):
        return None
    return a / b


def _placeholder_card(title: str, message: str) -> str:
    return f"""
    <div class=\"panel\">
      <div class=\"panel-head\">
        <h2>{title}</h2>
      </div>
      <div class=\"placeholder\">{message}</div>
    </div>
    """


def get_price(symbol: str, start_date: str, end_date: str | None = None, source: str | None = None) -> pd.Series:
    df = DataRouter.get_price_data(symbol, start_date, end_date=end_date, source=source)
    if df is None or df.empty:
        return _empty_series()
    close_col = "Close" if "Close" in df.columns else df.columns[0]
    return _clean_series(df[close_col].rename(symbol))


def build_composite(symbols: list[str], start_date: str, end_date: str | None = None, source: str | None = None) -> pd.Series:
    frames = []
    for symbol in symbols:
        series = get_price(symbol, start_date, end_date=end_date, source=source)
        if not series.empty:
            frames.append(_normalize_to_100(series).rename(symbol))
    if not frames:
        return _empty_series()
    combined = pd.concat(frames, axis=1).ffill().dropna(how="all")
    if combined.empty:
        return _empty_series()
    return combined.mean(axis=1).rename("Composite")


def signal_badge(label: str, color: str) -> str:
    return f'<span class="badge" style="border-color:{color};color:{color};">{label}</span>'


def fig_to_html(fig: go.Figure) -> str:
    return fig.to_html(full_html=False, include_plotlyjs=False, config={"displayModeBar": False, "responsive": True})


def implication_box(title: str, body: str, color: str) -> str:
    return f"""
    <div class=\"implication\" style=\"border-left-color:{color};\">
      <div class=\"implication-title\" style=\"color:{color};\">{title}</div>
      <div class=\"implication-body\">{body}</div>
    </div>
    """


def _basket_chip(symbol: str) -> str:
        label = TICKER_LABELS.get(symbol, symbol)
        return f'<span class="ticker-chip"><strong>{symbol}</strong><em>{label}</em></span>'


def basket_block(title: str, symbols: list[str], note: str) -> str:
        chips = "".join(_basket_chip(symbol) for symbol in symbols)
        return f"""
        <div class="basket-block">
            <div class="basket-head">
                <span class="basket-title">{title}</span>
                <span class="basket-note">{note}</span>
            </div>
            <div class="ticker-row">{chips}</div>
        </div>
        """


def _fmp_records_to_df(records) -> pd.DataFrame:
    if not isinstance(records, list) or not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"]).sort_values("date")
        df = df.set_index("date")
    return df


def _yfinance_statement_df(symbol: str, statement: str, periods: int = 8) -> pd.DataFrame:
    ticker = yf.Ticker(symbol)
    raw = getattr(ticker, statement, None)
    if raw is None or raw.empty:
        return pd.DataFrame()
    df = raw.T.copy()
    df.index = pd.to_datetime(df.index, errors="coerce")
    df = df[~df.index.isna()].sort_index()
    return df.tail(periods)


def _get_income_statement_df(client: FMPClient, symbol: str, periods: int = 8) -> pd.DataFrame:
    df = _fmp_records_to_df(client.get_income_statement(symbol, period="quarter"))
    if df.empty:
        df = _yfinance_statement_df(symbol, "quarterly_income_stmt", periods=periods)
    return df.tail(periods)


def _get_cash_flow_df(client: FMPClient, symbol: str, periods: int = 8) -> pd.DataFrame:
    df = _fmp_records_to_df(client.get_cash_flow(symbol, period="quarter"))
    if df.empty:
        df = _yfinance_statement_df(symbol, "quarterly_cashflow", periods=periods)
    return df.tail(periods)


def _fallback_tsmc_monthly_df(years: list[int]) -> pd.DataFrame:
    rows = []
    for year in years:
        for month, values in TSMC_OFFICIAL_MONTHLY_FALLBACK.get(year, {}).items():
            revenue, yoy = values
            rows.append({
                "date": pd.Timestamp(year=year, month=month, day=1),
                "revenue_twd_mn": revenue,
                "yoy_pct": yoy,
                "source": "official_fallback",
            })
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("date")


def _extract_first_numeric(text: str) -> float | None:
    if not text:
        return None
    cleaned = text.replace(",", "")
    match = re.search(r"-?\d+(?:\.\d+)?", cleaned)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def fetch_tsmc_monthly_revenue(years: list[int]) -> pd.DataFrame:
    rows = []
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    for year in years:
        url = f"https://investor.tsmc.com/english/monthly-revenue/{year}"
        try:
            response = session.get(url, timeout=20)
            response.raise_for_status()
        except Exception:
            continue
        soup = BeautifulSoup(response.text, "html.parser")
        tables = soup.find_all("table")
        parsed = False

        for table in tables:
            grid = []
            for tr in table.find_all("tr"):
                cells = [cell.get_text(" ", strip=True) for cell in tr.find_all(["th", "td"])]
                if cells:
                    grid.append(cells)
            if len(grid) < 3:
                continue

            header = " ".join(grid[0]).lower()
            if "month" not in header and "revenue" not in header and "net revenue" not in " ".join(sum(grid[:2], [])).lower():
                continue

            for row in grid[1:]:
                if not row:
                    continue
                month_num = _extract_first_numeric(row[0])
                if month_num is None or month_num < 1 or month_num > 12:
                    continue
                revenue = None
                yoy = None
                for cell in row[1:]:
                    if revenue is None:
                        revenue = _extract_first_numeric(cell)
                    if "%" in cell and yoy is None:
                        yoy = _extract_first_numeric(cell)
                if revenue is None:
                    continue
                date = pd.Timestamp(year=year, month=int(month_num), day=1)
                rows.append({"date": date, "revenue_twd_mn": revenue, "yoy_pct": yoy, "source": "live_scrape"})
                parsed = True
            if parsed:
                break

        if parsed:
            continue

        text = soup.get_text("\n", strip=True)
        pattern = re.compile(
            rf"{year}\s*/\s*(\d{{1,2}}).*?Net Revenue.*?([\d,]+(?:\.\d+)?) .*?(?:YoY|year-on-year).*?(-?\d+(?:\.\d+)?)%",
            re.IGNORECASE | re.DOTALL,
        )
        for match in pattern.finditer(text):
            month_num = int(match.group(1))
            revenue = float(match.group(2).replace(",", ""))
            yoy = float(match.group(3))
            rows.append({
                "date": pd.Timestamp(year=year, month=month_num, day=1),
                "revenue_twd_mn": revenue,
                "yoy_pct": yoy,
                "source": "regex_scrape",
            })

    df = pd.DataFrame(rows).drop_duplicates(subset=["date"]).sort_values("date") if rows else pd.DataFrame()
    fallback = _fallback_tsmc_monthly_df(years)
    if df.empty:
        return fallback
    merged = pd.concat([fallback, df], ignore_index=True).sort_values(["date", "source"])
    merged = merged.drop_duplicates(subset=["date"], keep="last")
    return merged.sort_values("date")


def build_space_economy_panel(start_date: str, end_date: str) -> tuple[str, dict]:
    pure_play = ["RKLB", "LUNR", "RDW", "ASTS", "PL"]
    defense = ["LMT", "NOC", "RTX", "GD", "LHX"]

    pure_series = build_composite(pure_play, start_date, end_date=end_date)
    defense_series = build_composite(defense, start_date, end_date=end_date)
    ufo_series = _normalize_to_100(get_price("UFO", start_date, end_date=end_date))

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=pure_series.index, y=pure_series.values, mode="lines", name="Space Pure-Play", line=dict(color=BLUE, width=3)))
    fig.add_trace(go.Scatter(x=defense_series.index, y=defense_series.values, mode="lines", name="Defense Basket", line=dict(color=GREEN, width=2)))
    fig.add_trace(go.Scatter(x=ufo_series.index, y=ufo_series.values, mode="lines", name="UFO ETF", line=dict(color=PURPLE, width=2, dash="dot")))
    fig.update_layout(title="Space Economy Leadership Map", yaxis_title="Indexed Return (100 = start)", **PLOTLY_LAYOUT)

    pure_1m = _pct_change(pure_series, 21)
    defense_1m = _pct_change(defense_series, 21)
    ufo_1m = _pct_change(ufo_series, 21)
    pure_ytd = _ytd_change(pure_series)
    defense_ytd = _ytd_change(defense_series)
    ufo_ytd = _ytd_change(ufo_series)

    candidates = {
        "Space Pure-Play": pure_1m,
        "Defense Basket": defense_1m,
        "UFO ETF": ufo_1m,
    }
    leader = max(candidates, key=lambda key: candidates[key] if candidates[key] is not None else float("-inf"))
    leader_value = candidates.get(leader)

    if leader == "Space Pure-Play" and (leader_value or 0) > 5:
        body = f"Pure-play space names are leading on both momentum and narrative intensity. 1M leadership is {_fmt_pct(pure_1m)} versus defense {_fmt_pct(defense_1m)} and UFO {_fmt_pct(ufo_1m)}."
        badge = signal_badge("Speculative Leadership", BLUE)
        color = BLUE
    elif leader == "Defense Basket":
        body = f"Institutional defense is outperforming the more speculative space cohort. That usually means the market wants exposure to the theme, but through durable cash-flow names."
        badge = signal_badge("Defense Confirming", GREEN)
        color = GREEN
    else:
        body = f"The theme is broad but not decisive. UFO is {_fmt_pct(ufo_1m)} over 1M while pure-play space is {_fmt_pct(pure_1m)} and defense is {_fmt_pct(defense_1m)}."
        badge = signal_badge("Mixed Breadth", YELLOW)
        color = YELLOW

    summary = {
        "leader_1m": leader,
        "pure_1m": pure_1m,
        "defense_1m": defense_1m,
        "ufo_1m": ufo_1m,
        "pure_ytd": pure_ytd,
        "defense_ytd": defense_ytd,
        "ufo_ytd": ufo_ytd,
    }

    html = f"""
    <div class="panel">
      <div class="panel-head">
        <h2>Space Economy</h2>
        <div>{badge}</div>
      </div>
            <div class="basket-stack">
                {basket_block("Pure-Play Space Basket", pure_play, "High-beta operators and infrastructure names driving speculative leadership")}
                {basket_block("Defense Basket", defense, "Cash-flow-heavy aerospace and defense incumbents for institutional confirmation")}
                {basket_block("Benchmark ETF", ["UFO"], "Broad listed space ETF used as the neutral theme reference")}
            </div>
      <div class="stats-row">
        <div class="stat"><span>Pure-Play 1M</span><strong>{_fmt_pct(pure_1m)}</strong></div>
        <div class="stat"><span>Defense 1M</span><strong>{_fmt_pct(defense_1m)}</strong></div>
        <div class="stat"><span>UFO 1M</span><strong>{_fmt_pct(ufo_1m)}</strong></div>
        <div class="stat"><span>1M Leader</span><strong>{leader}</strong></div>
      </div>
      {fig_to_html(fig)}
      {implication_box("Interpretation", body, color)}
    </div>
    """
    return html, summary


def build_tsmc_panel() -> tuple[str, dict]:
    df = fetch_tsmc_monthly_revenue([2024, 2025, 2026])
    if df.empty:
        raise RuntimeError("TSMC monthly revenue scrape returned no usable rows")

    df = df.sort_values("date")
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(x=df["date"], y=df["revenue_twd_mn"], name="Revenue (TWD mn)", marker_color=BLUE, opacity=0.75),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=df["date"], y=df["yoy_pct"], name="YoY %", mode="lines+markers", line=dict(color=GOLD, width=3)),
        secondary_y=True,
    )
    fig.update_layout(title="TSMC Monthly Revenue Pulse", **PLOTLY_LAYOUT)
    fig.update_yaxes(title_text="Revenue (TWD mn)", secondary_y=False)
    fig.update_yaxes(title_text="YoY %", secondary_y=True)

    latest = df.iloc[-1]
    yoy = latest.get("yoy_pct")
    revenue = latest.get("revenue_twd_mn")
    source = latest.get("source", "unknown")
    yoy_3m = pd.to_numeric(df["yoy_pct"], errors="coerce").dropna().tail(3)
    yoy_avg = yoy_3m.mean() if not yoy_3m.empty else None

    if yoy is not None and yoy >= 20:
        color = GREEN
        badge = signal_badge("Demand Acceleration", GREEN)
        body = f"TSMC monthly revenue is still running hot at {yoy:.1f}% YoY, with a 3-month average of {yoy_avg:.1f}% YoY. That keeps the upstream AI demand signal intact."
    elif yoy is not None and yoy >= 8:
        color = YELLOW
        badge = signal_badge("Healthy But Cooling", YELLOW)
        body = f"TSMC revenue is still positive at {yoy:.1f}% YoY, but the acceleration is less explosive. Watch whether the 3-month average of {yoy_avg:.1f}% keeps fading."
    else:
        color = RED
        badge = signal_badge("Demand Softening", RED)
        body = f"TSMC monthly revenue is no longer confirming a fresh acceleration regime. Latest YoY is {yoy if yoy is not None else float('nan'):.1f}% on revenue {revenue:,.0f}."

    summary = {
        "latest_yoy": yoy,
        "latest_revenue": revenue,
        "three_month_avg_yoy": yoy_avg,
        "source": source,
    }

    html = f"""
    <div class="panel subpanel">
      <div class="panel-head">
        <h3>1. TSMC Monthly Revenue</h3>
        <div>{badge}</div>
      </div>
            <div class="basket-stack">
                {basket_block("Upstream Foundry Pulse", ["TSM"], "Official TSMC monthly revenue is the first read on real AI silicon demand")}
            </div>
      {fig_to_html(fig)}
      {implication_box("Interpretation", body, color)}
    </div>
    """
    return html, summary


def build_memory_panel(client: FMPClient) -> tuple[str, dict]:
    mu_df = _get_income_statement_df(client, "MU", periods=8)
    comp_symbol = "SNDK"
    comp_df = _get_income_statement_df(client, comp_symbol, periods=8)
    if comp_df.empty:
        comp_symbol = "WDC"
        comp_df = _get_income_statement_df(client, comp_symbol, periods=8)
    if mu_df.empty or comp_df.empty:
        raise RuntimeError("Missing FMP quarterly income statement data for memory panel")

    mu_rev_col = "revenue" if "revenue" in mu_df.columns else "Total Revenue"
    comp_rev_col = "revenue" if "revenue" in comp_df.columns else "Total Revenue"
    mu_rev = pd.to_numeric(mu_df.get(mu_rev_col), errors="coerce").dropna()
    comp_rev = pd.to_numeric(comp_df.get(comp_rev_col), errors="coerce").dropna()

    mu_gm = None
    comp_gm = None
    if "grossProfitRatio" in mu_df.columns:
        mu_gm = pd.to_numeric(mu_df["grossProfitRatio"], errors="coerce").dropna() * 100
    elif {"grossProfit", "revenue"}.issubset(mu_df.columns):
        mu_gm = (pd.to_numeric(mu_df["grossProfit"], errors="coerce") / pd.to_numeric(mu_df["revenue"], errors="coerce") * 100).dropna()
    elif {"Gross Profit", "Total Revenue"}.issubset(mu_df.columns):
        mu_gm = (pd.to_numeric(mu_df["Gross Profit"], errors="coerce") / pd.to_numeric(mu_df["Total Revenue"], errors="coerce") * 100).dropna()

    if "grossProfitRatio" in comp_df.columns:
        comp_gm = pd.to_numeric(comp_df["grossProfitRatio"], errors="coerce").dropna() * 100
    elif {"grossProfit", "revenue"}.issubset(comp_df.columns):
        comp_gm = (pd.to_numeric(comp_df["grossProfit"], errors="coerce") / pd.to_numeric(comp_df["revenue"], errors="coerce") * 100).dropna()
    elif {"Gross Profit", "Total Revenue"}.issubset(comp_df.columns):
        comp_gm = (pd.to_numeric(comp_df["Gross Profit"], errors="coerce") / pd.to_numeric(comp_df["Total Revenue"], errors="coerce") * 100).dropna()

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=mu_rev.index, y=mu_rev.values / 1e9, name="MU Revenue ($B)", mode="lines+markers", line=dict(color=GREEN, width=3)), secondary_y=False)
    fig.add_trace(go.Scatter(x=comp_rev.index, y=comp_rev.values / 1e9, name=f"{comp_symbol} Revenue ($B)", mode="lines+markers", line=dict(color=BLUE, width=3)), secondary_y=False)
    if mu_gm is not None and not mu_gm.empty:
        fig.add_trace(go.Scatter(x=mu_gm.index, y=mu_gm.values, name="MU Gross Margin %", mode="lines", line=dict(color=LT_GREEN, dash="dash")), secondary_y=True)
    if comp_gm is not None and not comp_gm.empty:
        fig.add_trace(go.Scatter(x=comp_gm.index, y=comp_gm.values, name=f"{comp_symbol} Gross Margin %", mode="lines", line=dict(color=PURPLE, dash="dot")), secondary_y=True)
    fig.update_layout(title="Memory Demand Reality Check", **PLOTLY_LAYOUT)
    fig.update_yaxes(title_text="Revenue ($B)", secondary_y=False)
    fig.update_yaxes(title_text="Gross Margin %", secondary_y=True)

    mu_rev_growth = _pct_change(mu_rev, 3)
    comp_rev_growth = _pct_change(comp_rev, 3)
    mu_margin_latest = _latest_value(mu_gm) if mu_gm is not None else None
    comp_margin_latest = _latest_value(comp_gm) if comp_gm is not None else None

    if (mu_rev_growth or -999) > 0 and (comp_rev_growth or -999) > 0:
        color = GREEN
        badge = signal_badge("Broadening Demand", GREEN)
        body = f"Memory demand is no longer just a Micron story. MU revenue is {_fmt_pct(mu_rev_growth)} over the last three quarterly steps and {comp_symbol} is {_fmt_pct(comp_rev_growth)}."
    elif (mu_rev_growth or -999) > 0 and (comp_rev_growth or 999) <= 0:
        color = YELLOW
        badge = signal_badge("Leader-Laggard Split", YELLOW)
        body = f"Micron is confirming AI-linked memory strength, but the secondary comp is not yet fully validating it. MU is {_fmt_pct(mu_rev_growth)} while {comp_symbol} is {_fmt_pct(comp_rev_growth)} over the last three quarterly steps."
    else:
        color = RED
        badge = signal_badge("Patchy Confirmation", RED)
        body = f"The memory complex is not showing broad confirmation. MU is {_fmt_pct(mu_rev_growth)} and {comp_symbol} is {_fmt_pct(comp_rev_growth)} over the last three quarterly steps."

    summary = {
        "comp_symbol": comp_symbol,
        "mu_rev_growth": mu_rev_growth,
        "comp_rev_growth": comp_rev_growth,
        "mu_margin_latest": mu_margin_latest,
        "comp_margin_latest": comp_margin_latest,
    }

    html = f"""
    <div class="panel subpanel">
      <div class="panel-head">
        <h3>2. Memory Demand Reality</h3>
        <div>{badge}</div>
      </div>
            <div class="basket-stack">
                {basket_block("Lead Memory Name", ["MU"], "Primary AI memory leader used to test whether HBM demand is showing up in fundamentals")}
                {basket_block("Cross-Check Comparator", [comp_symbol], "Secondary memory read used to separate single-name strength from broad demand confirmation")}
            </div>
      {fig_to_html(fig)}
      {implication_box("Interpretation", body, color)}
    </div>
    """
    return html, summary


def build_capex_panel(client: FMPClient, start_date: str, end_date: str) -> tuple[str, dict]:
    mag7 = ["AAPL", "MSFT", "META", "AMZN", "GOOGL", "NVDA", "TSLA"]
    infra_basket = ["VRT", "ANET", "SMCI", "DELL", "EQIX"]

    capex_frames = []
    for symbol in mag7:
        cf_df = _get_cash_flow_df(client, symbol, periods=8)
        if cf_df.empty:
            continue
        capex_col = None
        for candidate in ["capitalExpenditure", "capitalExpenditures", "investmentsInPropertyPlantAndEquipment", "Capital Expenditure"]:
            if candidate in cf_df.columns:
                capex_col = candidate
                break
        if not capex_col:
            continue
        series = pd.to_numeric(cf_df[capex_col], errors="coerce").abs().dropna()
        if not series.empty:
            series.index = series.index.to_period("Q").to_timestamp("Q")
            series = series.groupby(series.index).last()
            capex_frames.append(series.rename(symbol))

    if not capex_frames:
        raise RuntimeError("No usable Mag7 cash-flow capex series returned from FMP")

    capex_df = pd.concat(capex_frames, axis=1).sort_index()
    coverage = capex_df.count(axis=1)
    min_coverage = max(4, math.ceil(len(capex_frames) * 0.6))
    capex_total = capex_df.sum(axis=1, min_count=1)
    capex_total = capex_total[coverage >= min_coverage].dropna().rename("Mag7 Capex")
    capex_index = _normalize_to_100(capex_total)
    infra_index = build_composite(infra_basket, start_date, end_date=end_date)
    if infra_index.empty:
        raise RuntimeError("No usable AI build-out basket price data returned")

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=capex_total.index, y=capex_total.values / 1e9, name="Mag7 Capex ($B)", mode="lines+markers", line=dict(color=GOLD, width=3)), secondary_y=False)
    fig.add_trace(go.Scatter(x=infra_index.index, y=infra_index.values, name="AI Build-out Basket (Index)", mode="lines", line=dict(color=BLUE, width=3)), secondary_y=True)
    fig.update_layout(title="Mag7 Capex vs AI Build-out", **PLOTLY_LAYOUT)
    fig.update_yaxes(title_text="Capex ($B)", secondary_y=False)
    fig.update_yaxes(title_text="Indexed Return", secondary_y=True)

    capex_growth = _pct_change(capex_total, 3)
    infra_3m = _pct_change(infra_index, 63)

    if (capex_growth or -999) > 10 and (infra_3m or -999) > 0:
        color = GREEN
        badge = signal_badge("Spend Confirmed", GREEN)
        body = f"Mag7 capex is still accelerating at {_fmt_pct(capex_growth)} over the last three quarterly steps, and downstream AI build-out equities are confirming at {_fmt_pct(infra_3m)} over 3M."
    elif (capex_growth or -999) > 10 and (infra_3m or 999) <= 0:
        color = YELLOW
        badge = signal_badge("Spend Ahead Of Equities", YELLOW)
        body = f"The capex signal is still firm at {_fmt_pct(capex_growth)}, but downstream infrastructure equities are not confirming it cleanly at {_fmt_pct(infra_3m)} over 3M."
    else:
        color = RED
        badge = signal_badge("Build-out Cooling", RED)
        body = f"Capex acceleration is not forceful enough to keep the AI build-out theme on a clean all-clear. Mag7 capex is {_fmt_pct(capex_growth)} across the last three quarterly steps."

    summary = {
        "capex_growth": capex_growth,
        "infra_3m": infra_3m,
    }

    html = f"""
    <div class="panel subpanel">
      <div class="panel-head">
        <h3>3. Mag7 Capex vs AI Data Center Build-out</h3>
        <div>{badge}</div>
      </div>
            <div class="basket-stack">
                {basket_block("Mag7 Capex Basket", mag7, "Quarterly capex aggregation measuring hyperscaler and platform AI spending capacity")}
                {basket_block("AI Build-out Equity Basket", infra_basket, "Downstream beneficiaries of power, networking, servers, and colocation demand")}
            </div>
      {fig_to_html(fig)}
      {implication_box("Interpretation", body, color)}
    </div>
    """
    return html, summary


def build_semi_equipment_panel(start_date: str, end_date: str) -> tuple[str, dict]:
    semi_equipment = ["AMAT", "LRCX", "KLAC", "ASML", "TER"]
    semi_index = build_composite(semi_equipment, start_date, end_date=end_date)
    tsm_index = _normalize_to_100(get_price("TSM", start_date, end_date=end_date))
    if semi_index.empty or tsm_index.empty:
        raise RuntimeError("Missing price data for semi equipment breadth panel")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=semi_index.index, y=semi_index.values, mode="lines", name="Semi Equipment Composite", line=dict(color=BRONZE, width=3)))
    fig.add_trace(go.Scatter(x=tsm_index.index, y=tsm_index.values, mode="lines", name="TSM ADR", line=dict(color=GREEN, width=3, dash="dash")))
    fig.update_layout(title="Semi Equipment Breadth vs TSM", yaxis_title="Indexed Return (100 = start)", **PLOTLY_LAYOUT)

    semi_3m = _pct_change(semi_index, 63)
    tsm_3m = _pct_change(tsm_index, 63)
    spread = None if semi_3m is None or tsm_3m is None else semi_3m - tsm_3m

    if spread is not None and spread > 5:
        color = GREEN
        badge = signal_badge("Breadth Expanding", GREEN)
        body = f"Equipment names are outperforming TSM by {spread:+.1f} points over 3M, which usually signals broadening foundry and tool demand rather than a single-stock squeeze."
    elif spread is not None and spread >= -5:
        color = YELLOW
        badge = signal_badge("In Sync", YELLOW)
        body = f"TSM and the equipment complex are moving together. Semi equipment is {_fmt_pct(semi_3m)} over 3M versus TSM at {_fmt_pct(tsm_3m)}."
    else:
        color = RED
        badge = signal_badge("Breadth Lagging", RED)
        body = f"TSM is not getting clean confirmation from the equipment complex. Semi equipment is {_fmt_pct(semi_3m)} over 3M versus TSM at {_fmt_pct(tsm_3m)}."

    summary = {
        "semi_3m": semi_3m,
        "tsm_3m": tsm_3m,
        "spread": spread,
    }

    html = f"""
    <div class="panel subpanel">
      <div class="panel-head">
        <h3>4. Semi Equipment Confirmation</h3>
        <div>{badge}</div>
      </div>
            <div class="basket-stack">
                {basket_block("Semi Equipment Basket", semi_equipment, "Tool and inspection names used to test whether equipment breadth confirms foundry demand")}
                {basket_block("Foundry Benchmark", ["TSM"], "TSMC ADR acts as the single-name foundry benchmark against the broader tool complex")}
            </div>
      {fig_to_html(fig)}
      {implication_box("Interpretation", body, color)}
    </div>
    """
    return html, summary


GLOBAL_CSS = f"""
body {{
  margin: 0;
  background: radial-gradient(circle at top, #182233 0%, {BG} 42%, #080b10 100%);
  color: {TEXT};
  font-family: Segoe UI, Arial, sans-serif;
}}
.wrap {{
  max-width: 1460px;
  margin: 0 auto;
  padding: 28px 24px 40px;
}}
.hero {{
  display: flex;
  justify-content: space-between;
  align-items: end;
  gap: 20px;
  margin-bottom: 24px;
}}
.hero h1 {{
  margin: 0;
  font-size: 34px;
  letter-spacing: 0.3px;
}}
.hero p {{
  margin: 6px 0 0;
  color: {MUTED};
  max-width: 920px;
  line-height: 1.45;
}}
.panel {{
  background: linear-gradient(180deg, rgba(22,27,34,0.96) 0%, rgba(13,17,23,0.98) 100%);
  border: 1px solid {BORDER};
  border-radius: 18px;
  padding: 18px 18px 12px;
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.22);
  margin-bottom: 22px;
}}
.subgrid {{
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}}
.panel-head {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 12px;
}}
.panel-head h2, .panel-head h3 {{
  margin: 0;
  font-weight: 700;
}}
.panel-head h3 {{
  font-size: 18px;
}}
.stats-row {{
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}}
.stat {{
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid {BORDER};
  background: rgba(255,255,255,0.02);
}}
.stat span {{
  display: block;
  color: {MUTED};
  font-size: 12px;
  margin-bottom: 6px;
}}
.stat strong {{
  font-size: 18px;
}}
.badge {{
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border: 1px solid;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.6px;
}}
.implication {{
  margin-top: 8px;
  padding: 12px 14px;
  background: rgba(255,255,255,0.03);
  border-left: 4px solid {BLUE};
  border-radius: 10px;
}}
.implication-title {{
  font-weight: 700;
  margin-bottom: 6px;
  text-transform: uppercase;
  font-size: 12px;
  letter-spacing: 0.8px;
}}
.implication-body {{
  color: {TEXT};
  line-height: 1.5;
}}
.basket-stack {{
    display: grid;
    gap: 10px;
    margin: 4px 0 14px;
}}
.basket-block {{
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 12px 14px;
    background: rgba(255,255,255,0.025);
}}
.basket-head {{
    display: flex;
    justify-content: space-between;
    gap: 12px;
    align-items: center;
    margin-bottom: 10px;
}}
.basket-title {{
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    color: {TEXT};
}}
.basket-note {{
    font-size: 12px;
    color: {MUTED};
}}
.ticker-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}}
.ticker-chip {{
    display: inline-flex;
    flex-direction: column;
    gap: 2px;
    padding: 8px 10px;
    border-radius: 10px;
    border: 1px solid rgba(255,255,255,0.08);
    background: rgba(255,255,255,0.03);
    min-width: 92px;
}}
.ticker-chip strong {{
    font-size: 12px;
    color: {TEXT};
}}
.ticker-chip em {{
    font-style: normal;
    font-size: 11px;
    color: {MUTED};
    line-height: 1.2;
}}
.placeholder {{
  padding: 20px;
  color: {MUTED};
  border: 1px dashed {BORDER};
  border-radius: 12px;
  background: rgba(255,255,255,0.02);
}}
.section-label {{
  font-size: 13px;
  color: {MUTED};
  letter-spacing: 2px;
  text-transform: uppercase;
  margin: 8px 0 16px;
}}
@media (max-width: 960px) {{
  .subgrid, .stats-row {{
    grid-template-columns: 1fr;
  }}
  .hero {{
    flex-direction: column;
    align-items: flex-start;
  }}
    .basket-head {{
        flex-direction: column;
        align-items: flex-start;
    }}
}}
"""


def build_dashboard() -> tuple[str, dict]:
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d")
    client = FMPClient()
    summary = {}

    panels = []
    try:
        space_html, summary["space"] = build_space_economy_panel(start_date, end_date)
        panels.append(space_html)
    except Exception as exc:
        summary["space"] = {"error": str(exc)}
        panels.append(_placeholder_card("Space Economy", f"Space panel unavailable: {exc}"))

    ai_panels = []
    try:
        html, summary["tsmc"] = build_tsmc_panel()
        ai_panels.append(html)
    except Exception as exc:
        summary["tsmc"] = {"error": str(exc)}
        ai_panels.append(_placeholder_card("1. TSMC Monthly Revenue", f"TSMC panel unavailable: {exc}"))

    try:
        html, summary["memory"] = build_memory_panel(client)
        ai_panels.append(html)
    except Exception as exc:
        summary["memory"] = {"error": str(exc)}
        ai_panels.append(_placeholder_card("2. Memory Demand Reality", f"Memory panel unavailable: {exc}"))

    try:
        html, summary["capex"] = build_capex_panel(client, start_date, end_date)
        ai_panels.append(html)
    except Exception as exc:
        summary["capex"] = {"error": str(exc)}
        ai_panels.append(_placeholder_card("3. Mag7 Capex vs AI Data Center Build-out", f"Capex panel unavailable: {exc}"))

    try:
        html, summary["semi"] = build_semi_equipment_panel(start_date, end_date)
        ai_panels.append(html)
    except Exception as exc:
        summary["semi"] = {"error": str(exc)}
        ai_panels.append(_placeholder_card("4. Semi Equipment Confirmation", f"Semi equipment panel unavailable: {exc}"))

    panels.append(f"""
    <div class="panel">
      <div class="panel-head">
        <h2>AI Demand Cycle</h2>
        <div>{signal_badge('Theme Signal Deck', GOLD)}</div>
      </div>
      <div class="section-label">Upstream demand, memory reality, hyperscaler spend, and equipment breadth</div>
      <div class="subgrid">{''.join(ai_panels)}</div>
    </div>
    """)

    timestamp = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y-%m-%d %I:%M %p CT")
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>Theme Signal Intelligence</title>
      <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
      <style>{GLOBAL_CSS}</style>
    </head>
    <body>
      <div class="wrap">
        <div class="hero">
          <div>
            <h1>Theme Signal Intelligence</h1>
            <p>Standalone study dashboard tracking whether institutional price action and quarterly fundamentals are confirming the current Space Economy and AI Demand narratives.</p>
          </div>
          <div>{signal_badge(timestamp, BLUE)}</div>
        </div>
        {''.join(panels)}
      </div>
    </body>
    </html>
    """
    return html, summary


def print_signal_summary(summary: dict) -> None:
    print("\nSIGNAL SUMMARY")
    print("-" * 72)

    space = summary.get("space", {})
    if "error" in space:
        print(f"Space Economy: unavailable ({space['error']})")
    else:
        print(
            "Space Economy: "
            f"1M leader={space.get('leader_1m')} | pure={_fmt_pct(space.get('pure_1m'))} | "
            f"defense={_fmt_pct(space.get('defense_1m'))} | UFO={_fmt_pct(space.get('ufo_1m'))}"
        )

    tsmc = summary.get("tsmc", {})
    if "error" in tsmc:
        print(f"TSMC Monthly Revenue: unavailable ({tsmc['error']})")
    else:
        latest_yoy = tsmc.get("latest_yoy")
        avg_yoy = tsmc.get("three_month_avg_yoy")
        print(
            "TSMC Monthly Revenue: "
            f"latest_yoy={latest_yoy:.1f}% | 3m_avg={avg_yoy:.1f}%" if latest_yoy is not None and avg_yoy is not None else
            "TSMC Monthly Revenue: partial data"
        )

    memory = summary.get("memory", {})
    if "error" in memory:
        print(f"Memory Demand Reality: unavailable ({memory['error']})")
    else:
        print(
            "Memory Demand Reality: "
            f"MU={_fmt_pct(memory.get('mu_rev_growth'))} | {memory.get('comp_symbol')}={_fmt_pct(memory.get('comp_rev_growth'))}"
        )

    capex = summary.get("capex", {})
    if "error" in capex:
        print(f"Mag7 Capex vs AI Build-out: unavailable ({capex['error']})")
    else:
        print(
            "Mag7 Capex vs AI Build-out: "
            f"capex_growth={_fmt_pct(capex.get('capex_growth'))} | infra_3m={_fmt_pct(capex.get('infra_3m'))}"
        )

    semi = summary.get("semi", {})
    if "error" in semi:
        print(f"Semi Equipment Confirmation: unavailable ({semi['error']})")
    else:
        spread = semi.get("spread")
        spread_text = "N/A" if spread is None else f"{spread:+.1f} pts"
        print(
            "Semi Equipment Confirmation: "
            f"semi_3m={_fmt_pct(semi.get('semi_3m'))} | tsm_3m={_fmt_pct(semi.get('tsm_3m'))} | spread={spread_text}"
        )


def main() -> None:
    print("Building Theme Signal Intelligence dashboard...")
    load_keys("paper")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    html, summary = build_dashboard()
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print(f"Dashboard written to {OUTPUT_FILE}")
    print_signal_summary(summary)
    if os.environ.get("QUANTLAB_NO_OPEN") != "1":
        try:
            os.startfile(str(OUTPUT_FILE))
            print("Opened dashboard in browser.")
        except Exception as exc:
            print(f"Could not auto-open browser: {exc}")


if __name__ == "__main__":
    main()