"""
╔══════════════════════════════════════════════════════════════════════╗
║  DELL — Historical Realized Volatility & Expected Move Analysis     ║
║  Date: February 27, 2026                                           ║
║  Purpose: Compute HV at multiple lookbacks, IV percentile rank,    ║
║           and options-implied expected move for front week/monthly. ║
╚══════════════════════════════════════════════════════════════════════╝

Uses:
  - DataRouter for historical OHLCV (Alpaca primary)
  - Current ATM IV from today's levels engine run (49.4% monthly)
  - yfinance for supplemental IV/options snapshot
"""

import sys
import os
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from pathlib import Path
import json
import warnings
warnings.filterwarnings('ignore')

import yfinance as yf

# ═══════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════

TICKER = "DELL"
SPOT = 147.12  # from today's levels engine run
ATM_IV_MONTHLY = 0.4935  # 49.35% from March 20 monthly lens
MONTHLY_EXPIRY = "2026-03-20"
TODAY = "2026-02-27"

# Lookback for historical data (need ~1.5 years for good IV percentile)
START_DATE = "2024-06-01"
END_DATE = TODAY

# HV windows (trading days)
HV_WINDOWS = [10, 20, 30, 60, 90, 252]

OUTPUT_DIR = Path(r'C:\QuantLab\Data_Lab\data\levels\2026-02-27')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════
# PHASE 1: FETCH HISTORICAL DATA
# ═══════════════════════════════════════════════════════

print("=" * 70)
print(f"  DELL — HISTORICAL IV & EXPECTED MOVE ANALYSIS")
print("=" * 70)

print(f"\n📊 Fetching {TICKER} daily data ({START_DATE} → {END_DATE})...")
raw = yf.download(TICKER, start=START_DATE, end=END_DATE, progress=False, auto_adjust=True)
if raw.empty:
    raise RuntimeError(f"yfinance returned no data for {TICKER}")

# Normalize columns: yfinance may return MultiIndex for single tickers
if isinstance(raw.columns, pd.MultiIndex):
    raw.columns = raw.columns.droplevel(1)
df = raw.rename(columns=lambda c: c.lower())

print(f"   Rows returned: {len(df)}")
print(f"   Date range: {df.index[0]} → {df.index[-1]}")
print(f"   Last close: ${df['close'].iloc[-1]:.2f}")


# ═══════════════════════════════════════════════════════
# PHASE 2: COMPUTE REALIZED VOLATILITY (HV)
# ═══════════════════════════════════════════════════════

print(f"\n{'─' * 70}")
print(f"  REALIZED VOLATILITY (ANNUALIZED)")
print(f"{'─' * 70}")

# Log returns
df['log_return'] = np.log(df['close'] / df['close'].shift(1))
df['daily_return_pct'] = df['close'].pct_change() * 100

# Compute HV for each window
hv_results = {}
for window in HV_WINDOWS:
    col_name = f'HV{window}'
    df[col_name] = df['log_return'].rolling(window).std() * np.sqrt(252) * 100
    current_hv = df[col_name].iloc[-1]
    hv_results[window] = current_hv
    if not np.isnan(current_hv):
        print(f"  HV{window:>3d} (current): {current_hv:6.1f}%")
    else:
        print(f"  HV{window:>3d} (current): N/A (insufficient data)")

# Yang-Zhang volatility estimator (OHLC-based, more efficient)
def yang_zhang_vol(df_ohlc, window=20):
    """Yang-Zhang volatility estimator using OHLC data."""
    log_ho = np.log(df_ohlc['high'] / df_ohlc['open'])
    log_lo = np.log(df_ohlc['low'] / df_ohlc['open'])
    log_co = np.log(df_ohlc['close'] / df_ohlc['open'])
    log_oc = np.log(df_ohlc['open'] / df_ohlc['close'].shift(1))
    
    rs = log_ho * (log_ho - log_co) + log_lo * (log_lo - log_co)
    
    close_vol = df_ohlc['log_return'].rolling(window).var()
    open_vol = log_oc.rolling(window).var()
    window_rs = rs.rolling(window).mean()
    
    k = 0.34 / (1.34 + (window + 1) / (window - 1))
    yz_var = open_vol + k * close_vol + (1 - k) * window_rs
    
    return np.sqrt(yz_var * 252) * 100

df['YZ_Vol_20'] = yang_zhang_vol(df, 20)
yz_current = df['YZ_Vol_20'].iloc[-1]
if not np.isnan(yz_current):
    print(f"\n  Yang-Zhang 20d: {yz_current:6.1f}%  (OHLC-based, more efficient estimator)")


# ═══════════════════════════════════════════════════════
# PHASE 3: IV vs HV CONTEXT
# ═══════════════════════════════════════════════════════

print(f"\n{'─' * 70}")
print(f"  IMPLIED vs REALIZED VOLATILITY")
print(f"{'─' * 70}")

atm_iv_pct = ATM_IV_MONTHLY * 100
hv20 = hv_results.get(20, np.nan)
hv30 = hv_results.get(30, np.nan)

print(f"  Current ATM IV (Mar 20 monthly): {atm_iv_pct:.1f}%")
print(f"  Current HV20:                    {hv20:.1f}%")
print(f"  Current HV30:                    {hv30:.1f}%")

if not np.isnan(hv20):
    iv_hv_premium = atm_iv_pct - hv20
    iv_hv_ratio = atm_iv_pct / hv20
    print(f"\n  IV − HV20 premium:  {iv_hv_premium:+.1f}%")
    print(f"  IV / HV20 ratio:    {iv_hv_ratio:.2f}x")
    
    if iv_hv_premium > 10:
        print(f"  🔴 IV is ELEVATED relative to realized — options are expensive")
    elif iv_hv_premium > 5:
        print(f"  🟡 IV is MODERATELY above realized — slight premium")
    elif iv_hv_premium > -5:
        print(f"  🟢 IV is FAIR relative to realized")
    else:
        print(f"  🔵 IV is CHEAP relative to realized — options are underpriced")


# ═══════════════════════════════════════════════════════
# PHASE 4: HV PERCENTILE RANK (IV RANK PROXY)
# ═══════════════════════════════════════════════════════

print(f"\n{'─' * 70}")
print(f"  VOLATILITY PERCENTILE RANKINGS")
print(f"{'─' * 70}")

# Compute percentile of current HV vs its own history
for window in [20, 30, 60]:
    col = f'HV{window}'
    series = df[col].dropna()
    if len(series) > 20:
        current = series.iloc[-1]
        pctile = (series < current).sum() / len(series) * 100
        hi = series.max()
        lo = series.min()
        print(f"  HV{window} percentile rank: {pctile:.0f}th  "
              f"(range: {lo:.1f}% – {hi:.1f}%, current: {current:.1f}%)")

# IV percentile estimate using HV20 as proxy
# (since we only have single-point IV, rank current IV vs HV history)
hv20_series = df['HV20'].dropna()
if len(hv20_series) > 20:
    iv_pctile = (hv20_series < atm_iv_pct).sum() / len(hv20_series) * 100
    print(f"\n  ⭐ IV Percentile Rank (vs HV20 history): {iv_pctile:.0f}th")
    print(f"     (Current IV {atm_iv_pct:.1f}% vs {len(hv20_series)} days of HV20 history)")


# ═══════════════════════════════════════════════════════
# PHASE 5: EXPECTED MOVE CALCULATION
# ═══════════════════════════════════════════════════════

print(f"\n{'─' * 70}")
print(f"  EXPECTED MOVE (OPTIONS-IMPLIED)")
print(f"{'─' * 70}")

today_dt = date.fromisoformat(TODAY)
monthly_dt = date.fromisoformat(MONTHLY_EXPIRY)
dte_monthly = (monthly_dt - today_dt).days

# Weekly expected move (next 5 trading days / ~7 calendar days)
dte_weekly = 7
weekly_em = SPOT * ATM_IV_MONTHLY * np.sqrt(dte_weekly / 365)
weekly_em_pct = (weekly_em / SPOT) * 100

# Monthly expected move (to March 20 OPEX)
monthly_em = SPOT * ATM_IV_MONTHLY * np.sqrt(dte_monthly / 365)
monthly_em_pct = (monthly_em / SPOT) * 100

# 1-day expected move
daily_em = SPOT * ATM_IV_MONTHLY / np.sqrt(252)
daily_em_pct = (daily_em / SPOT) * 100

# 1 standard deviation ranges
print(f"  Spot:  ${SPOT:.2f}")
print(f"  IV:    {atm_iv_pct:.1f}%  (ATM, Mar 20 monthly)")
print(f"  DTE to Mar OPEX: {dte_monthly} calendar days")
print()

print(f"  ┌─────────────────────────────────────────────────────────────┐")
print(f"  │  TIMEFRAME      │ ±1σ MOVE   │ ±$ RANGE           │ %     │")
print(f"  ├─────────────────┼────────────┼────────────────────┼───────┤")
print(f"  │  1 Day           │ ±${daily_em:.2f}    │ ${SPOT - daily_em:.2f} – ${SPOT + daily_em:.2f}  │ ±{daily_em_pct:.1f}% │")
print(f"  │  1 Week (7 cal)  │ ±${weekly_em:.2f}   │ ${SPOT - weekly_em:.2f} – ${SPOT + weekly_em:.2f} │ ±{weekly_em_pct:.1f}% │")
print(f"  │  Mar OPEX ({dte_monthly}d)  │ ±${monthly_em:.2f}  │ ${SPOT - monthly_em:.2f} – ${SPOT + monthly_em:.2f} │ ±{monthly_em_pct:.1f}% │")
print(f"  └─────────────────────────────────────────────────────────────┘")
print()

# ±2σ ranges
print(f"  2σ ranges (95% probability):")
print(f"    1 Week:   ${SPOT - 2*weekly_em:.2f} – ${SPOT + 2*weekly_em:.2f}")
print(f"    Mar OPEX: ${SPOT - 2*monthly_em:.2f} – ${SPOT + 2*monthly_em:.2f}")


# ═══════════════════════════════════════════════════════
# PHASE 6: RECENT PRICE ACTION CONTEXT
# ═══════════════════════════════════════════════════════

print(f"\n{'─' * 70}")
print(f"  RECENT PRICE ACTION (LAST 20 SESSIONS)")
print(f"{'─' * 70}")

recent = df.tail(20).copy()

# Stats
recent_high = recent['high'].max()
recent_low = recent['low'].min()
recent_range_pct = (recent_high - recent_low) / recent_low * 100
avg_daily_range = ((recent['high'] - recent['low']) / recent['open'] * 100).mean()
avg_abs_return = recent['daily_return_pct'].abs().mean()
max_up = recent['daily_return_pct'].max()
max_down = recent['daily_return_pct'].min()

print(f"  20-day high:           ${recent_high:.2f}")
print(f"  20-day low:            ${recent_low:.2f}")
print(f"  20-day range:          {recent_range_pct:.1f}%")
print(f"  Avg daily range (H-L): {avg_daily_range:.2f}%")
print(f"  Avg |daily return|:    {avg_abs_return:.2f}%")
print(f"  Largest up day:        +{max_up:.2f}%")
print(f"  Largest down day:      {max_down:.2f}%")


# ═══════════════════════════════════════════════════════
# PHASE 7: HISTORICAL VOL REGIME TABLE
# ═══════════════════════════════════════════════════════

print(f"\n{'─' * 70}")
print(f"  HV20 HISTORY (LAST 30 DATA POINTS, WEEKLY INTERVALS)")
print(f"{'─' * 70}")

# Sample HV20 at weekly intervals
hv20_hist = df[['close', 'HV20']].dropna().iloc[::5].tail(30)
print(f"  {'Date':<12} {'Close':>8} {'HV20':>8}")
print(f"  {'─'*12} {'─'*8} {'─'*8}")
for idx, row in hv20_hist.iterrows():
    dt_str = idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)[:10]
    print(f"  {dt_str:<12} ${row['close']:>7.2f} {row['HV20']:>7.1f}%")


# ═══════════════════════════════════════════════════════
# PHASE 8: TRY YFINANCE FOR ADDITIONAL IV DATA
# ═══════════════════════════════════════════════════════

print(f"\n{'─' * 70}")
print(f"  YFINANCE OPTIONS CHAIN SNAPSHOT (SUPPLEMENTAL)")
print(f"{'─' * 70}")

try:
    import yfinance as yf
    tick = yf.Ticker(TICKER)
    
    # Get available expiration dates
    expirations = tick.options
    print(f"  Available expirations: {len(expirations)}")
    
    # Find nearest weekly and monthly expiration
    for i, exp in enumerate(expirations[:5]):
        print(f"    [{i}] {exp}")
    
    # Get the nearest expiration chain for ATM straddle
    if expirations:
        # Find closest to March 20
        best_exp = None
        best_diff = float('inf')
        for exp in expirations:
            diff = abs((date.fromisoformat(exp) - monthly_dt).days)
            if diff < best_diff:
                best_diff = diff
                best_exp = exp
        
        print(f"\n  Closest to Mar OPEX: {best_exp} (diff: {best_diff}d)")
        
        chain = tick.option_chain(best_exp)
        calls = chain.calls
        puts = chain.puts
        
        # Find ATM straddle
        atm_strike_candidates = calls['strike'].values
        atm_idx = np.argmin(np.abs(atm_strike_candidates - SPOT))
        atm_strike = atm_strike_candidates[atm_idx]
        
        atm_call = calls[calls['strike'] == atm_strike].iloc[0]
        atm_put = puts[puts['strike'] == atm_strike].iloc[0]
        
        straddle_price = atm_call['lastPrice'] + atm_put['lastPrice']
        straddle_pct = straddle_price / SPOT * 100
        
        call_iv = atm_call.get('impliedVolatility', 0) * 100
        put_iv = atm_put.get('impliedVolatility', 0) * 100
        avg_iv = (call_iv + put_iv) / 2
        
        print(f"\n  ATM Strike: ${atm_strike:.0f}")
        print(f"  ATM Call:   ${atm_call['lastPrice']:.2f}  (IV: {call_iv:.1f}%, OI: {atm_call.get('openInterest', 'N/A')})")
        print(f"  ATM Put:    ${atm_put['lastPrice']:.2f}  (IV: {put_iv:.1f}%, OI: {atm_put.get('openInterest', 'N/A')})")
        print(f"  Straddle:   ${straddle_price:.2f}  ({straddle_pct:.1f}% of spot)")
        print(f"  Avg ATM IV: {avg_iv:.1f}%")
        
        # Expected move from straddle price (more direct)
        straddle_em = straddle_price * 0.85  # ~85% of straddle ≈ 1σ expected move
        print(f"\n  📍 Straddle-implied expected move to {best_exp}:")
        print(f"     ±${straddle_em:.2f}  →  ${SPOT - straddle_em:.2f} – ${SPOT + straddle_em:.2f}")
        
        # Get front-week chain too if available
        if len(expirations) >= 2:
            front_exp = expirations[0]
            front_chain = tick.option_chain(front_exp)
            front_calls = front_chain.calls
            front_puts = front_chain.puts
            
            f_atm_idx = np.argmin(np.abs(front_calls['strike'].values - SPOT))
            f_atm_strike = front_calls['strike'].values[f_atm_idx]
            
            f_atm_call = front_calls[front_calls['strike'] == f_atm_strike].iloc[0]
            f_atm_put = front_puts[front_puts['strike'] == f_atm_strike].iloc[0]
            
            f_straddle = f_atm_call['lastPrice'] + f_atm_put['lastPrice']
            f_call_iv = f_atm_call.get('impliedVolatility', 0) * 100
            f_put_iv = f_atm_put.get('impliedVolatility', 0) * 100
            f_avg_iv = (f_call_iv + f_put_iv) / 2
            
            print(f"\n  Front-week chain ({front_exp}):")
            print(f"    ATM Strike: ${f_atm_strike:.0f}")
            print(f"    ATM Call: ${f_atm_call['lastPrice']:.2f}  (IV: {f_call_iv:.1f}%)")
            print(f"    ATM Put:  ${f_atm_put['lastPrice']:.2f}  (IV: {f_put_iv:.1f}%)")
            print(f"    Straddle: ${f_straddle:.2f}  ({f_straddle/SPOT*100:.1f}% of spot)")
            print(f"    Avg ATM IV: {f_avg_iv:.1f}%")

except Exception as e:
    print(f"  ⚠️  yfinance options fetch failed: {e}")
    print(f"  (This is supplemental only — Alpaca IV data above is primary)")


# ═══════════════════════════════════════════════════════
# PHASE 9: EARNINGS PROXIMITY CHECK
# ═══════════════════════════════════════════════════════

print(f"\n{'─' * 70}")
print(f"  EARNINGS PROXIMITY & IV CONTEXT")
print(f"{'─' * 70}")

# DELL typically reports in late Feb / early March
# Check if the elevated IV might be earnings-related
print(f"  ⚠️  NOTE: DELL reports earnings Q4 FY2026 around this date.")
print(f"  Current ATM IV of {atm_iv_pct:.1f}% may include EARNINGS PREMIUM.")
print(f"  If earnings have already passed, IV should crush significantly.")
print(f"  If earnings are upcoming, the straddle price reflects the")
print(f"  market's expected earnings move + time value.")

if not np.isnan(hv20):
    earnings_premium_est = atm_iv_pct - hv20
    if earnings_premium_est > 10:
        print(f"\n  📊 Estimated earnings IV premium: ~{earnings_premium_est:.0f}%")
        print(f"     (ATM IV {atm_iv_pct:.1f}% minus HV20 {hv20:.1f}%)")


# ═══════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════

print(f"\n{'=' * 70}")
print(f"  SUMMARY — DELL IV & EXPECTED MOVE")
print(f"{'=' * 70}")
print(f"  Spot:              ${SPOT:.2f}")
print(f"  ATM IV (monthly):  {atm_iv_pct:.1f}%")
if not np.isnan(hv20):
    print(f"  HV20 (realized):   {hv20:.1f}%")
    print(f"  IV/HV premium:     {atm_iv_pct - hv20:+.1f}%")
print(f"  Daily EM:          ±${daily_em:.2f}  ({daily_em_pct:.1f}%)")
print(f"  Weekly EM:         ±${weekly_em:.2f}  ({weekly_em_pct:.1f}%)")
print(f"  Mar OPEX EM:       ±${monthly_em:.2f}  ({monthly_em_pct:.1f}%)")
print(f"  Mar OPEX 1σ range: ${SPOT - monthly_em:.2f} – ${SPOT + monthly_em:.2f}")
print(f"  Mar OPEX 2σ range: ${SPOT - 2*monthly_em:.2f} – ${SPOT + 2*monthly_em:.2f}")
print(f"{'=' * 70}")
