"""
Combined IV / HV / Short Interest / Gamma Regime analysis for DELL & RUN.
Outputs structured data used to build the weekly README.
"""
import sys, warnings
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
from datetime import date
import yfinance as yf
import json

TICKERS = {
    "DELL": {"spot": 147.12, "atm_iv": 0.4935, "monthly_exp": "2026-03-20"},
    "RUN":  {"spot": 12.68,  "atm_iv": 0.999,  "monthly_exp": "2026-03-20"},
}

TODAY = "2026-02-27"
today_dt = date.fromisoformat(TODAY)

results = {}

for ticker, cfg in TICKERS.items():
    spot = cfg["spot"]
    atm_iv = cfg["atm_iv"]
    monthly_dt = date.fromisoformat(cfg["monthly_exp"])
    dte = (monthly_dt - today_dt).days

    print(f"\n{'='*70}")
    print(f"  {ticker}  |  Spot: ${spot:.2f}  |  ATM IV: {atm_iv*100:.1f}%")
    print(f"{'='*70}")

    # --- Historical data ---
    start = "2024-01-01" if ticker == "DELL" else "2023-01-01"
    raw = yf.download(ticker, start=start, end=TODAY, progress=False, auto_adjust=True)
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.droplevel(1)
    df = raw.rename(columns=lambda c: c.lower())

    df['log_return'] = np.log(df['close'] / df['close'].shift(1))
    df['daily_return_pct'] = df['close'].pct_change() * 100

    # --- HV ---
    hv = {}
    for w in [10, 20, 30, 60]:
        col = f'HV{w}'
        df[col] = df['log_return'].rolling(w).std() * np.sqrt(252) * 100
        hv[w] = round(float(df[col].iloc[-1]), 1)
        print(f"  HV{w}: {hv[w]}%")

    # --- HV percentiles ---
    hv20_series = df['HV20'].dropna()
    hv20_pctile = round(float((hv20_series < hv[20]).sum() / len(hv20_series) * 100))
    iv_pctile = round(float((hv20_series < atm_iv*100).sum() / len(hv20_series) * 100))
    print(f"  HV20 percentile: {hv20_pctile}th")
    print(f"  IV percentile (vs HV20): {iv_pctile}th")

    # --- IV vs HV ---
    iv_hv_premium = round(atm_iv * 100 - hv[20], 1)
    iv_hv_ratio = round(atm_iv * 100 / hv[20], 2) if hv[20] > 0 else 0
    print(f"  IV-HV20 premium: {iv_hv_premium:+.1f}%  |  Ratio: {iv_hv_ratio}x")

    # --- Expected moves ---
    daily_em = spot * atm_iv / np.sqrt(252)
    weekly_em = spot * atm_iv * np.sqrt(7 / 365)
    monthly_em = spot * atm_iv * np.sqrt(dte / 365)

    # --- Recent price action ---
    recent = df.tail(20)
    r_high = float(recent['high'].max())
    r_low = float(recent['low'].min())
    r_range_pct = round((r_high - r_low) / r_low * 100, 1)
    avg_daily_range = round(float(((recent['high'] - recent['low']) / recent['open'] * 100).mean()), 2)
    avg_abs_ret = round(float(recent['daily_return_pct'].abs().mean()), 2)
    max_up = round(float(recent['daily_return_pct'].max()), 2)
    max_down = round(float(recent['daily_return_pct'].min()), 2)

    # --- Short interest via yfinance ---
    tick = yf.Ticker(ticker)
    info = tick.info or {}
    si_shares = info.get('sharesShort', None)
    si_pct_float = info.get('shortPercentOfFloat', None)
    si_ratio = info.get('shortRatio', None)  # days to cover
    si_prev = info.get('sharesShortPriorMonth', None)
    shares_out = info.get('sharesOutstanding', None)
    float_shares = info.get('floatShares', None)

    print(f"  Short Interest: {si_shares:,} shares" if si_shares else "  Short Interest: N/A")
    if si_pct_float:
        print(f"  Short % of Float: {si_pct_float*100:.1f}%" if si_pct_float < 1 else f"  Short % of Float: {si_pct_float:.1f}%")
    if si_ratio:
        print(f"  Days to Cover: {si_ratio:.1f}")

    # --- Options chain for straddle ---
    straddle_price = None
    straddle_call_iv = None
    straddle_put_iv = None
    try:
        exps = tick.options
        # Find closest to monthly
        best_exp = min(exps, key=lambda e: abs((date.fromisoformat(e) - monthly_dt).days))
        chain = tick.option_chain(best_exp)
        calls = chain.calls
        puts = chain.puts
        
        atm_idx = np.argmin(np.abs(calls['strike'].values - spot))
        atm_strike = calls['strike'].values[atm_idx]
        atm_call = calls[calls['strike'] == atm_strike].iloc[0]
        atm_put = puts[puts['strike'] == atm_strike].iloc[0]
        
        straddle_price = float(atm_call['lastPrice'] + atm_put['lastPrice'])
        straddle_call_iv = float(atm_call.get('impliedVolatility', 0) * 100)
        straddle_put_iv = float(atm_put.get('impliedVolatility', 0) * 100)
        
        print(f"  Straddle ({best_exp}, ${atm_strike}): ${straddle_price:.2f}")
        print(f"  Call IV: {straddle_call_iv:.1f}%  Put IV: {straddle_put_iv:.1f}%")
    except Exception as e:
        print(f"  Straddle fetch failed: {e}")

    # --- Gamma regime estimate ---
    # Simplified: if spot is above the highest-OI put strike and below
    # the highest-OI call strike, we're in "neutral gamma". If below put wall,
    # "negative gamma" (volatility expands). If above call wall, "positive gamma"
    # but capped.
    # We use the levels engine JSON for this.
    gamma_regime = "UNKNOWN"
    try:
        json_path = rf'C:\QuantLab\Data_Lab\data\levels\2026-02-27\query_output_{ticker}.json'
        with open(json_path) as f:
            levels_data = json.load(f)
        
        monthly_levels = levels_data.get('lens_monthly', {}).get('levels', [])
        
        # Find the strongest put wall and call wall
        put_walls = [l for l in monthly_levels if 'PUT' in l.get('type', '')]
        call_walls = [l for l in monthly_levels if 'CALL' in l.get('type', '')]
        
        strongest_put = max(put_walls, key=lambda x: x['oi']) if put_walls else None
        strongest_call = max(call_walls, key=lambda x: x['oi']) if call_walls else None
        
        # Also find the high-volume / step-change strikes near spot
        near_spot = [l for l in monthly_levels if abs(l['strike'] - spot) / spot < 0.15]
        
        if strongest_put and strongest_call:
            put_strike = strongest_put['strike']
            call_strike = strongest_call['strike']
            
            if spot < put_strike:
                gamma_regime = "NEGATIVE GAMMA"
                gamma_desc = f"Below major put wall (${put_strike}). Dealer hedging amplifies moves. Expect expanded volatility."
            elif spot > call_strike:
                gamma_regime = "POSITIVE GAMMA (CAPPED)"
                gamma_desc = f"Above call wall (${call_strike}). Dealer hedging dampens moves but creates resistance."
            elif spot >= put_strike and spot <= call_strike:
                dist_to_put = (spot - put_strike) / spot * 100
                dist_to_call = (call_strike - spot) / spot * 100
                if dist_to_put < 5 or dist_to_call < 5:
                    gamma_regime = "TRANSITION ZONE"
                    gamma_desc = f"Between ${put_strike} put wall and ${call_strike} call wall, but close to boundary. Hedging flows can shift quickly."
                else:
                    gamma_regime = "NEUTRAL/POSITIVE GAMMA"
                    gamma_desc = f"Between ${put_strike} put wall and ${call_strike} call wall. Dealer hedging dampens moves (mean-reversion tendency)."
        else:
            gamma_desc = "Insufficient wall data for regime determination."
            
        print(f"  Gamma Regime: {gamma_regime}")
        print(f"    {gamma_desc}")
    except Exception as e:
        gamma_desc = f"Could not determine: {e}"
        print(f"  Gamma Regime: {gamma_regime} ({e})")

    # Store results
    results[ticker] = {
        "spot": spot,
        "atm_iv": round(atm_iv * 100, 1),
        "hv": hv,
        "hv20_pctile": hv20_pctile,
        "iv_pctile": iv_pctile,
        "iv_hv_premium": iv_hv_premium,
        "iv_hv_ratio": iv_hv_ratio,
        "daily_em": round(daily_em, 2),
        "weekly_em": round(weekly_em, 2),
        "monthly_em": round(monthly_em, 2),
        "dte": dte,
        "recent_high": r_high,
        "recent_low": r_low,
        "recent_range_pct": r_range_pct,
        "avg_daily_range": avg_daily_range,
        "avg_abs_return": avg_abs_ret,
        "max_up": max_up,
        "max_down": max_down,
        "si_shares": si_shares,
        "si_pct_float": si_pct_float,
        "si_ratio": si_ratio,
        "si_prev_month": si_prev,
        "shares_outstanding": shares_out,
        "float_shares": float_shares,
        "straddle_price": straddle_price,
        "straddle_call_iv": straddle_call_iv,
        "straddle_put_iv": straddle_put_iv,
        "gamma_regime": gamma_regime,
        "gamma_desc": gamma_desc,
    }

# Save JSON for README builder
out_path = r'C:\QuantLab\Data_Lab\data\levels\2026-02-27\weekly_analysis_data.json'
with open(out_path, 'w') as f:
    json.dump(results, f, indent=2, default=str)
print(f"\n\n✅ Analysis data saved to {out_path}")

# Print summary
for t, r in results.items():
    print(f"\n{'─'*50}")
    print(f"  {t} QUICK SUMMARY")
    print(f"{'─'*50}")
    print(f"  Spot: ${r['spot']}  |  ATM IV: {r['atm_iv']}%  |  HV20: {r['hv'][20]}%")
    print(f"  IV-HV premium: {r['iv_hv_premium']:+.1f}%  |  IV rank: {r['iv_pctile']}th")
    print(f"  Gamma: {r['gamma_regime']}")
    if r['si_shares']:
        si_pct = r['si_pct_float']
        si_str = f"{si_pct*100:.1f}%" if si_pct and si_pct < 1 else (f"{si_pct:.1f}%" if si_pct else "N/A")
        print(f"  SI: {r['si_shares']:,} ({si_str} of float)  |  Days to cover: {r['si_ratio']}")
    print(f"  Daily EM: ±${r['daily_em']}  |  Weekly EM: ±${r['weekly_em']}  |  OPEX EM: ±${r['monthly_em']}")
