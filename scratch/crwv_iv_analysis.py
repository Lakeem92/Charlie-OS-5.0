"""
╔══════════════════════════════════════════════════════════════════════╗
║  CRWV (CoreWeave) — Historical Vol, IV Context & $80 Chop Analysis ║
║  Date: February 27, 2026                                           ║
║  Purpose: HV profile, IV context, expected move, and options       ║
║           positioning analysis explaining the $80 chop zone.       ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import sys
sys.path.insert(0, r'C:\QuantLab\Data_Lab')

import pandas as pd
import numpy as np
from datetime import date
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

import yfinance as yf

# ═══════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════

TICKER = "CRWV"
SPOT = 78.47  # from levels engine
ATM_IV_MONTHLY = 0.994  # 99.4% from March 20 monthly lens
MONTHLY_EXPIRY = "2026-03-20"
TODAY = "2026-02-27"

# CoreWeave IPO'd March 28, 2025 — limited history
START_DATE = "2025-03-28"
END_DATE = TODAY

HV_WINDOWS = [10, 20, 30, 60, 90]

# SEC arb levels from levels engine
ARB_LEVELS = {
    87.20: "Purchase/offering price — 8-K filed 2026-01-26",
    2.00: "Par value / aggregate price reference — 8-K filed 2026-01-26",
}

# Key options levels from levels engine
KEY_LEVELS = {
    80.0: {"front_oi": 6535, "front_vol": 30529, "monthly_oi": 23557, "monthly_vol": 9662, "tag": "HIGH VOLUME / STEP-CHANGE"},
    100.0: {"front_oi": 6794, "front_vol": 5832, "monthly_oi": 109382, "monthly_vol": 25892, "tag": "CALL WALL"},
    70.0: {"front_oi": 14484, "front_vol": 6423, "monthly_oi": 15012, "monthly_vol": 33046, "tag": "PUT WALL"},
    75.0: {"front_oi": 5123, "front_vol": 10238, "monthly_oi": 11001, "monthly_vol": 4522, "tag": "PUT WALL / STEP-CHANGE"},
    85.0: {"front_oi": 7431, "front_vol": 11009, "monthly_oi": 8320, "monthly_vol": 7090, "tag": "HIGH VOLUME / STEP-CHANGE"},
    90.0: {"front_oi": 5797, "front_vol": 7056, "monthly_oi": 15289, "monthly_vol": 1866, "tag": "STEP-CHANGE"},
    95.0: {"front_oi": 8035, "front_vol": 4095, "monthly_oi": 17538, "monthly_vol": 824, "tag": "STEP-CHANGE"},
}


# ═══════════════════════════════════════════════════════
# PHASE 1: FETCH HISTORICAL DATA
# ═══════════════════════════════════════════════════════

print("=" * 70)
print(f"  CRWV (CoreWeave) — IV, EXPECTED MOVE & $80 CHOP ANALYSIS")
print("=" * 70)

print(f"\n📊 Fetching {TICKER} daily data ({START_DATE} → {END_DATE})...")
raw = yf.download(TICKER, start=START_DATE, end=END_DATE, progress=False, auto_adjust=True)
if raw.empty:
    raise RuntimeError(f"yfinance returned no data for {TICKER}")

if isinstance(raw.columns, pd.MultiIndex):
    raw.columns = raw.columns.droplevel(1)
df = raw.rename(columns=lambda c: c.lower())

print(f"   Rows: {len(df)}  |  Range: {df.index[0].date()} → {df.index[-1].date()}")
print(f"   Last close: ${df['close'].iloc[-1]:.2f}  |  Spot (Alpaca): ${SPOT:.2f}")


# ═══════════════════════════════════════════════════════
# PHASE 2: REALIZED VOLATILITY
# ═══════════════════════════════════════════════════════

print(f"\n{'─' * 70}")
print(f"  REALIZED VOLATILITY (ANNUALIZED)")
print(f"{'─' * 70}")

df['log_return'] = np.log(df['close'] / df['close'].shift(1))
df['daily_return_pct'] = df['close'].pct_change() * 100

hv_results = {}
for window in HV_WINDOWS:
    col = f'HV{window}'
    df[col] = df['log_return'].rolling(window).std() * np.sqrt(252) * 100
    current_hv = df[col].iloc[-1]
    hv_results[window] = current_hv
    if not np.isnan(current_hv):
        print(f"  HV{window:>3d}: {current_hv:6.1f}%")
    else:
        print(f"  HV{window:>3d}: N/A")


# ═══════════════════════════════════════════════════════
# PHASE 3: IV vs HV
# ═══════════════════════════════════════════════════════

print(f"\n{'─' * 70}")
print(f"  IMPLIED vs REALIZED VOLATILITY")
print(f"{'─' * 70}")

atm_iv_pct = ATM_IV_MONTHLY * 100
hv20 = hv_results.get(20, np.nan)
hv30 = hv_results.get(30, np.nan)

print(f"  ATM IV (Mar 20 monthly):  {atm_iv_pct:.1f}%")
print(f"  HV20 (realized):          {hv20:.1f}%")
print(f"  HV30 (realized):          {hv30:.1f}%")

if not np.isnan(hv20):
    premium = atm_iv_pct - hv20
    ratio = atm_iv_pct / hv20
    print(f"\n  IV − HV20 premium:  {premium:+.1f}%")
    print(f"  IV / HV20 ratio:    {ratio:.2f}x")
    
    if premium > 15:
        print(f"  🔴 IV is VERY ELEVATED — options expensive relative to realized")
    elif premium > 5:
        print(f"  🟡 IV is ELEVATED — moderate premium")
    elif premium > -5:
        print(f"  🟢 IV is FAIR relative to realized")
    else:
        print(f"  🔵 IV is CHEAP — options underpriced vs realized")


# ═══════════════════════════════════════════════════════
# PHASE 4: VOL PERCENTILE RANKINGS
# ═══════════════════════════════════════════════════════

print(f"\n{'─' * 70}")
print(f"  VOLATILITY PERCENTILE RANKINGS")
print(f"{'─' * 70}")

for window in [20, 30, 60]:
    col = f'HV{window}'
    series = df[col].dropna()
    if len(series) > 10:
        current = series.iloc[-1]
        pctile = (series < current).sum() / len(series) * 100
        hi = series.max()
        lo = series.min()
        print(f"  HV{window} percentile: {pctile:.0f}th  "
              f"(range: {lo:.1f}% – {hi:.1f}%, current: {current:.1f}%)")

# IV rank vs HV20 history
hv20_series = df['HV20'].dropna()
if len(hv20_series) > 10:
    iv_pctile = (hv20_series < atm_iv_pct).sum() / len(hv20_series) * 100
    print(f"\n  ⭐ IV Percentile Rank (vs HV20 history): {iv_pctile:.0f}th")


# ═══════════════════════════════════════════════════════
# PHASE 5: EXPECTED MOVE
# ═══════════════════════════════════════════════════════

print(f"\n{'─' * 70}")
print(f"  EXPECTED MOVE (OPTIONS-IMPLIED)")
print(f"{'─' * 70}")

today_dt = date.fromisoformat(TODAY)
monthly_dt = date.fromisoformat(MONTHLY_EXPIRY)
dte_monthly = (monthly_dt - today_dt).days

daily_em = SPOT * ATM_IV_MONTHLY / np.sqrt(252)
daily_em_pct = daily_em / SPOT * 100

weekly_em = SPOT * ATM_IV_MONTHLY * np.sqrt(7 / 365)
weekly_em_pct = weekly_em / SPOT * 100

monthly_em = SPOT * ATM_IV_MONTHLY * np.sqrt(dte_monthly / 365)
monthly_em_pct = monthly_em / SPOT * 100

print(f"  Spot:  ${SPOT:.2f}")
print(f"  IV:    {atm_iv_pct:.1f}%  (ATM, Mar 20 monthly)")
print(f"  DTE:   {dte_monthly} calendar days to Mar OPEX")
print()
print(f"  ┌──────────────────────────────────────────────────────────────────┐")
print(f"  │  TIMEFRAME       │ ±1σ MOVE    │ ±$ RANGE              │ %      │")
print(f"  ├──────────────────┼─────────────┼───────────────────────┼────────┤")
print(f"  │  1 Day            │ ±${daily_em:.2f}     │ ${SPOT-daily_em:.2f} – ${SPOT+daily_em:.2f}    │ ±{daily_em_pct:.1f}%  │")
print(f"  │  1 Week (7 cal)   │ ±${weekly_em:.2f}   │ ${SPOT-weekly_em:.2f} – ${SPOT+weekly_em:.2f}  │ ±{weekly_em_pct:.1f}%  │")
print(f"  │  Mar OPEX ({dte_monthly}d)   │ ±${monthly_em:.2f}  │ ${SPOT-monthly_em:.2f} – ${SPOT+monthly_em:.2f} │ ±{monthly_em_pct:.1f}% │")
print(f"  └──────────────────────────────────────────────────────────────────┘")
print()
print(f"  2σ ranges (95% probability):")
print(f"    1 Week:   ${SPOT - 2*weekly_em:.2f} – ${SPOT + 2*weekly_em:.2f}")
print(f"    Mar OPEX: ${SPOT - 2*monthly_em:.2f} – ${SPOT + 2*monthly_em:.2f}")


# ═══════════════════════════════════════════════════════
# PHASE 6: $80 CHOP ZONE ANALYSIS
# ═══════════════════════════════════════════════════════

print(f"\n{'─' * 70}")
print(f"  WHY $80 IS A CHOP ZONE — OPTIONS POSITIONING ANALYSIS")
print(f"{'─' * 70}")

print(f"""
  The $80 strike is the single largest options battleground in CRWV:

  FRONT WEEK (0DTE, Feb 27):
    $80 strike:  OI = 6,535  |  Volume = 30,529  ← MASSIVE turnover
    This is the HIGHEST VOLUME strike on the entire chain today.
    
  MONTHLY (Mar 20 OPEX):
    $80 strike:  OI = 23,557  |  Volume = 9,662
    This is the HIGHEST OI strike near spot on the monthly.

  WHY THIS CAUSES CHOP:
  ─────────────────────
  1. DEALER HEDGING GRAVITY (PINNING EFFECT):
     When a strike has enormous OI relative to surrounding strikes,
     dealers who sold those options must continuously delta-hedge.
     - Below $80: dealers buy shares (pushes price up)
     - Above $80: dealers sell shares (pushes price down)
     This creates a "pinning magnet" that pulls price back to $80.

  2. BATTLE LINE DYNAMICS:
     30,529 contracts traded today at the $80 strike alone.
     Both calls AND puts are heavily traded → two-sided war.
     Neither side can sustain a breakout because the opposing
     hedging flow kicks in immediately.

  3. STRUCTURAL CEILING — ARB LEVEL AT $87.20:
     SEC filing (8-K, Jan 26, 2026) shows a share purchase at $87.20.
     This is a VERIFIED contractual level from the levels engine.
     Structural participants (insiders, institutions from the offering)
     may be natural sellers near this price → resistance cap.

  4. SUPPORTIVE PUT WALLS BELOW:
     $75: OI 5,123 / 11,001  (front/monthly)
     $70: OI 14,484 / 15,012  (front/monthly) ← MAJOR FLOOR
     These put walls provide mechanical support, preventing a flush
     below $75-70 and keeping price in the $70-$85 range.

  5. CALL WALL AT $100 (MONTHLY = 109,382 OI):
     This is a MASSIVE call wall. Until $80-$85-$90 clear with
     sustained volume, the $100 wall acts as an asymptotic ceiling.

  NET EFFECT:
  ───────────
  Price is TRAPPED between the $70 put wall floor and the $85-$87.20
  resistance cluster (options OI + SEC arb level). The $80 strike sits
  right in the middle of this range with the highest activity, creating
  maximum chop and two-sided hedging flow.""")


# ═══════════════════════════════════════════════════════
# PHASE 7: HISTORICAL PRICE ACTION AROUND $80
# ═══════════════════════════════════════════════════════

print(f"\n{'─' * 70}")
print(f"  PRICE ACTION STATISTICS AROUND $80")
print(f"{'─' * 70}")

# Count how many days price touched the $78-$82 zone
zone_low, zone_high = 78.0, 82.0
in_zone = df[(df['low'] <= zone_high) & (df['high'] >= zone_low)]
total_days = len(df)
zone_days = len(in_zone)
zone_pct = zone_days / total_days * 100

print(f"  Days price touched $78-$82 zone: {zone_days} / {total_days} ({zone_pct:.0f}%)")

# Days closing in the zone
close_in_zone = df[(df['close'] >= zone_low) & (df['close'] <= zone_high)]
print(f"  Days closing in $78-$82:         {len(close_in_zone)} ({len(close_in_zone)/total_days*100:.0f}%)")

# Average daily range when in the zone vs outside
in_zone_range = ((in_zone['high'] - in_zone['low']) / in_zone['open'] * 100).mean()
out_zone = df[~df.index.isin(in_zone.index)]
if len(out_zone) > 0:
    out_zone_range = ((out_zone['high'] - out_zone['low']) / out_zone['open'] * 100).mean()
    print(f"  Avg daily range IN zone:         {in_zone_range:.2f}%")
    print(f"  Avg daily range OUTSIDE zone:    {out_zone_range:.2f}%")

# Recent price action
print(f"\n  Last 20 sessions:")
recent = df.tail(20)
r_high = recent['high'].max()
r_low = recent['low'].min()
r_range = (r_high - r_low) / r_low * 100
avg_daily_range = ((recent['high'] - recent['low']) / recent['open'] * 100).mean()
avg_abs_ret = recent['daily_return_pct'].abs().mean()
max_up = recent['daily_return_pct'].max()
max_down = recent['daily_return_pct'].min()

print(f"    20-day high:           ${r_high:.2f}")
print(f"    20-day low:            ${r_low:.2f}")
print(f"    20-day range:          {r_range:.1f}%")
print(f"    Avg daily range (H-L): {avg_daily_range:.2f}%")
print(f"    Avg |daily return|:    {avg_abs_ret:.2f}%")
print(f"    Largest up day:        +{max_up:.2f}%")
print(f"    Largest down day:      {max_down:.2f}%")

# Crosses through $80 
df['crossed_80'] = ((df['low'] < 80) & (df['high'] > 80))
crosses = df['crossed_80'].sum()
print(f"\n  Days straddling $80 (low<80, high>80): {crosses}")


# ═══════════════════════════════════════════════════════
# PHASE 8: YFINANCE OPTIONS SNAPSHOT
# ═══════════════════════════════════════════════════════

print(f"\n{'─' * 70}")
print(f"  YFINANCE OPTIONS SNAPSHOT (SUPPLEMENTAL)")
print(f"{'─' * 70}")

try:
    tick = yf.Ticker(TICKER)
    expirations = tick.options
    print(f"  Available expirations: {len(expirations)}")
    for i, exp in enumerate(expirations[:6]):
        print(f"    [{i}] {exp}")
    
    # Get March monthly chain
    best_exp = None
    for exp in expirations:
        if exp == MONTHLY_EXPIRY:
            best_exp = exp
            break
    if not best_exp:
        best_exp = expirations[0]
        best_diff = abs((date.fromisoformat(expirations[0]) - monthly_dt).days)
        for exp in expirations:
            diff = abs((date.fromisoformat(exp) - monthly_dt).days)
            if diff < best_diff:
                best_diff = diff
                best_exp = exp
    
    print(f"\n  Using expiration: {best_exp}")
    
    chain = tick.option_chain(best_exp)
    calls = chain.calls
    puts = chain.puts
    
    # ATM straddle
    atm_idx = np.argmin(np.abs(calls['strike'].values - SPOT))
    atm_strike = calls['strike'].values[atm_idx]
    atm_call = calls[calls['strike'] == atm_strike].iloc[0]
    atm_put = puts[puts['strike'] == atm_strike].iloc[0]
    
    straddle = atm_call['lastPrice'] + atm_put['lastPrice']
    straddle_pct = straddle / SPOT * 100
    call_iv = atm_call.get('impliedVolatility', 0) * 100
    put_iv = atm_put.get('impliedVolatility', 0) * 100
    
    print(f"\n  ATM Strike: ${atm_strike:.0f}")
    print(f"  ATM Call:   ${atm_call['lastPrice']:.2f}  (IV: {call_iv:.1f}%, OI: {atm_call.get('openInterest', 'N/A')})")
    print(f"  ATM Put:    ${atm_put['lastPrice']:.2f}  (IV: {put_iv:.1f}%, OI: {atm_put.get('openInterest', 'N/A')})")
    print(f"  Straddle:   ${straddle:.2f}  ({straddle_pct:.1f}% of spot)")
    
    straddle_em = straddle * 0.85
    print(f"\n  📍 Straddle-implied EM to {best_exp}:")
    print(f"     ±${straddle_em:.2f}  →  ${SPOT - straddle_em:.2f} – ${SPOT + straddle_em:.2f}")
    
    # Show $80 strike specifically
    print(f"\n  $80 STRIKE DETAIL (Mar OPEX):")
    c80 = calls[calls['strike'] == 80].iloc[0] if 80 in calls['strike'].values else None
    p80 = puts[puts['strike'] == 80].iloc[0] if 80 in puts['strike'].values else None
    if c80 is not None:
        print(f"    $80 Call: ${c80['lastPrice']:.2f}  IV: {c80.get('impliedVolatility',0)*100:.1f}%  OI: {c80.get('openInterest','N/A')}  Vol: {c80.get('volume','N/A')}")
    if p80 is not None:
        print(f"    $80 Put:  ${p80['lastPrice']:.2f}  IV: {p80.get('impliedVolatility',0)*100:.1f}%  OI: {p80.get('openInterest','N/A')}  Vol: {p80.get('volume','N/A')}")

except Exception as e:
    print(f"  ⚠️  yfinance options failed: {e}")


# ═══════════════════════════════════════════════════════
# PHASE 9: HV HISTORY TABLE
# ═══════════════════════════════════════════════════════

print(f"\n{'─' * 70}")
print(f"  HV20 TIME SERIES (WEEKLY SAMPLES)")
print(f"{'─' * 70}")

hv20_hist = df[['close', 'HV20']].dropna().iloc[::5].tail(30)
print(f"  {'Date':<12} {'Close':>8} {'HV20':>8}")
print(f"  {'─'*12} {'─'*8} {'─'*8}")
for idx, row in hv20_hist.iterrows():
    dt_str = idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)[:10]
    print(f"  {dt_str:<12} ${row['close']:>7.2f} {row['HV20']:>7.1f}%")


# ═══════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════

print(f"\n{'=' * 70}")
print(f"  SUMMARY — CRWV OPTIONS & IV PROFILE")
print(f"{'=' * 70}")
print(f"  Spot:              ${SPOT:.2f}")
print(f"  ATM IV (monthly):  {atm_iv_pct:.1f}%")
if not np.isnan(hv20):
    print(f"  HV20 (realized):   {hv20:.1f}%")
    print(f"  IV/HV premium:     {atm_iv_pct - hv20:+.1f}%")
print(f"  Daily EM:          ±${daily_em:.2f}  ({daily_em_pct:.1f}%)")
print(f"  Weekly EM:         ±${weekly_em:.2f}  ({weekly_em_pct:.1f}%)")
print(f"  Mar OPEX EM:       ±${monthly_em:.2f}  ({monthly_em_pct:.1f}%)")
print(f"  Mar 1σ range:      ${SPOT - monthly_em:.2f} – ${SPOT + monthly_em:.2f}")
print(f"  Mar 2σ range:      ${SPOT - 2*monthly_em:.2f} – ${SPOT + 2*monthly_em:.2f}")
print(f"\n  SEC ARB LEVELS:")
for price, desc in sorted(ARB_LEVELS.items(), reverse=True):
    dist = (price - SPOT) / SPOT * 100
    print(f"    ${price:.2f}  ({dist:+.1f}% from spot) — {desc}")
print(f"\n  $80 CHOP: {crosses} days straddled $80 | "
      f"Front-week volume = 30,529 (highest strike)")
print(f"{'=' * 70}")
