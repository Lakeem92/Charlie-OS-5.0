# MU Earnings Intraday Volatility Expansion & Substitution Study

## Executive Summary

**Research Question:** On MU earnings days, is MU itself the best intraday volatility vehicle—or do correlated semiconductor names consistently exhibit earlier, larger, and cleaner ATR-normalized expansion for day trades?

**Study Type:** Price/Volatility Study (Intraday) - Pure OHLCV measurement

**Key Innovation:** CORRECTED earnings-to-session mapping ensures all metrics are computed on the proper trading session:
- **BMO (Before Market Open)** announcements → analyzed on SAME trading day
- **AMC (After Market Close)** announcements → analyzed on NEXT trading day
- ATR normalization uses data strictly PRIOR to event session

---

## Methodology

### Data Sources
- **Price Data:** Alpaca Markets (API-SAFE, event-filtered pulls only)
- **Earnings Calendar:** Financial Modeling Prep (FMP) API with timestamps
- **Timeframe:** 2016-01-01 to present
- **Bar Size:** 5-minute intraday bars
- **Timezone:** Central Time (CT)

### Universe
**Primary:** MU (Micron Technology)

**Cohort Candidates:**
NVDA, AMD, AVGO, QCOM, INTC, TXN, AMAT, LRCX, KLAC, ASML, TSM, MRVL, ON, MPWR, MCHP, ADI, ALAB

### Sessions Analyzed
- **Premarket:** 3:00 AM - 8:29 AM CT (included for context)
- **RTH (Regular Trading Hours):** 8:30 AM - 3:00 PM CT (primary analysis)

### MU Regime Classification
Each MU earnings day is classified based on MU's open-to-close return:
- **UPSIDE:** return > +1.0%
- **DOWNSIDE:** return < -1.0%
- **FLAT/IN-LINE:** |return| ≤ 1.0%

---

## Metrics Computed

### 1. Volatility Expansion Metrics (ATR-Normalized)
Per ticker, per event:
- **Max Excursion from Open:** Largest directional move (high or low) / ATR(14)
- **Full Day Range:** (High - Low) / ATR(14)
- **Time-to-Expansion:** Minutes to reach 0.5, 1.0, 1.5 ATR from RTH open
- **Session Breakdowns:**
  - Premarket max excursion
  - Morning session (8:30-11:00) max excursion
  - Full-day max excursion

### 2. Path Quality Metrics
Per ticker, per event:
- **Directional Efficiency:** |open-to-close| / full_range (cleaner = higher)
- **Reversal Count:** Number of counter-moves ≥ 0.3 ATR from extremes
- **Wick/Body Ratio:** Average bar wick size relative to body (cleaner = lower)
- **CLV (Close Location Value):** Average bar close position within range
- **ORB Breakout:** Did price break the first 15-minute range?

### 3. Regime-Conditioned Rankings
Per MU regime (UPSIDE, DOWNSIDE, FLAT):
- Average max excursion (ATR)
- % of days hitting 1.0 ATR expansion
- Average time-to-1.0 ATR (minutes)
- Average directional efficiency
- Average reversal count
- Composite rank (equal-weighted: expansion + speed + cleanness)

---

## Critical Correction: Earnings-to-Session Mapping

### The Problem
Raw earnings announcement dates are ambiguous. An announcement on "2024-12-18" could mean:
- **BMO (Before Market Open):** Announced before 8:30 AM → analyze 2024-12-18 session
- **AMC (After Market Close):** Announced after 4:00 PM → analyze 2024-12-19 session

Using the wrong session invalidates:
- Open/close definitions
- ATR normalization (mixing pre-event and post-event data)
- Time-to-expansion metrics
- Regime labeling

### The Fix (Implemented)
**Step A:** Retrieve earnings with announcement_datetime (timezone-aware)

**Step B:** Classify timing:
- BMO if announcement_time < 8:30 AM CT
- AMC if announcement_time ≥ 4:00 PM CT
- INVALID if during market hours (8:30 AM - 4:00 PM CT) → excluded

**Step C:** Map to event_session_date:
- BMO → SAME trading day
- AMC → NEXT trading day

**Step D:** ATR alignment:
- ATR(14) computed using ONLY data PRIOR to event_session_date
- Never mixes same-day partial data

**Step E:** API-SAFE filtering:
- Intraday bars pulled ONLY for event_session_date
- No continuous intraday history requests

---

## How to Run

### Prerequisites
```powershell
# From Data_Lab root, activate virtual environment
.venv\Scripts\Activate.ps1

# Verify APIs configured
# - ALPACA_API_KEY
# - ALPACA_API_SECRET
# - FMP_API_KEY
```

### Execution
```powershell
# Navigate to study folder
cd studies\mu_intraday_earnings

# Run the study
python run_mu_intraday_earnings_study.py
```

### Expected Runtime
- Earnings calendar fetch: ~5 seconds
- Daily ATR calculation (18 tickers): ~30-60 seconds
- Intraday data fetch (18 tickers × ~30 events): ~5-10 minutes
- Metrics computation: ~30-60 seconds

**Total:** ~8-12 minutes (depends on API rate limits)

---

## Outputs

All files saved to `outputs/` subdirectory:

### 1. `mu_intraday_atr_expansion.csv`
Row per (event_date, ticker) with columns:
- ticker, event_date, regime
- atr, ticker_open, max_high, min_low
- open_high_exc_pct, open_low_exc_pct, max_exc_pct, range_pct
- open_high_atr, open_low_atr, max_exc_atr, range_atr
- time_to_0.5atr, time_to_1.0atr, time_to_1.5atr
- premarket_max_exc_atr, morning_max_exc_atr

### 2. `mu_intraday_path_quality.csv`
Row per (event_date, ticker) with columns:
- ticker, event_date, regime
- directional_efficiency
- reversal_count
- avg_wick_ratio
- avg_clv_rth
- orb_breakout

### 3. `mu_intraday_rankings_by_regime.csv`
Row per (regime, ticker) with columns:
- regime, ticker, sample_size
- avg_max_exc_atr, avg_range_atr
- pct_hit_1atr, avg_time_to_1.0atr
- avg_directional_efficiency, avg_reversal_count, avg_wick_ratio
- rank_expansion, rank_speed, rank_clean, composite_rank

### 4. `run_log.txt`
Complete execution log including:
- All parameters used
- Earnings date alignment fix documentation
- Sample size summary (BMO vs AMC)
- Regime distribution
- Data quality metrics
- Composite ranking formula (fixed weights)

---

## Interpretation Guide

### What to Look For

**1. MU Baseline vs Cohort**
- Does MU consistently rank high in its own earnings days?
- Or do other tickers systematically move earlier/larger/cleaner?

**2. Regime-Specific Substitution**
- Example: On MU UPSIDE days, does NVDA or AMD expand faster?
- On MU DOWNSIDE days, does INTC exhibit cleaner paths?

**3. Speed-to-Expansion**
- Which tickers hit 1.0 ATR within first 30 minutes?
- Useful for targeting early-session entries

**4. Path Cleanness**
- Lower reversal_count = more directional
- Higher directional_efficiency = less chop
- Lower avg_wick_ratio = fewer fake-outs

**5. Consistency**
- pct_hit_1atr: What % of events reached 1 ATR expansion?
- High percentage + fast speed = reliable volatility vehicle

### Example Findings (Hypothetical)

**UPSIDE Regime:**
- MU: avg_max_exc_atr = 1.8, time_to_1atr = 45 min, reversal_count = 3.2
- NVDA: avg_max_exc_atr = 2.4, time_to_1atr = 28 min, reversal_count = 2.1
- **Interpretation:** NVDA expands 33% more than MU, 37% faster, with fewer reversals

**DOWNSIDE Regime:**
- MU: avg_max_exc_atr = 1.5, pct_hit_1atr = 67%
- KLAC: avg_max_exc_atr = 2.1, pct_hit_1atr = 85%
- **Interpretation:** KLAC more reliable volatility on MU negative earnings

---

## Trading Applications

### Strategy Development
**DO NOT use this study for trade advice.** This is pure statistical research.

However, the outputs CAN inform:
1. **Instrument selection:** Which ticker to watch on MU earnings day
2. **Entry timing:** When do reliable moves typically begin?
3. **Volatility expectations:** How much intraday range to expect (ATR-normalized)
4. **Path quality filters:** Avoid tickers with high chop (high reversal_count)

### Risk Management Insights
- If MU itself is low-ranked, consider cohort names have HIGHER risk
- Premarket_max_exc_atr: Did most move happen before open? (less RTH opportunity)
- Morning_max_exc_atr: Was move concentrated early? (late entries risky)

---

## Limitations & Constraints

1. **Sample Size Dependent:**
   - Study only as good as number of MU earnings events in date range
   - Minimum 15-20 events recommended for statistical validity

2. **Regime Balance:**
   - If all earnings are UPSIDE, DOWNSIDE rankings will be sparse
   - Check run_log.txt for regime distribution

3. **Liquidity Not Measured:**
   - Study doesn't account for spread, slippage, or order book depth
   - High ATR expansion means nothing if ticker is illiquid

4. **No Execution Simulation:**
   - Metrics assume you can trade at any point in the bar
   - Real fills may differ significantly

5. **Correlation ≠ Causation:**
   - Co-movement may be sector-wide, not MU-driven
   - Need to verify MU is the catalyst vs broader semi news

---

## Validation Checklist

Before trusting results, verify:

- [ ] run_log.txt shows balanced BMO/AMC classification (not all one type)
- [ ] Sample size ≥ 15 valid event sessions
- [ ] Regime distribution not heavily skewed (not 100% UPSIDE)
- [ ] ATR records match event count × ticker count
- [ ] Expansion/quality CSV files not full of NaN values
- [ ] Time-to-expansion metrics have reasonable values (<120 min for 1 ATR)
- [ ] Rankings show variety (not all tickers tied)

---

## Next Steps

### Immediate
1. Run study and review outputs
2. Identify top-3 ranked tickers per regime
3. Manually verify 2-3 specific events in TradingView or ThinkOrSwim

### Follow-Up Research
1. **Liquidity Filter:** Add average volume threshold
2. **VIX Regime:** Does pattern hold in high-VIX vs low-VIX environments?
3. **Earnings Beat/Miss:** Does magnitude of MU earnings surprise affect cohort?
4. **Sector ETF (SMH):** Does SMH move predictably vs individual names?
5. **Forward Returns:** Do high-expansion days predict multi-day continuation?

---

## Data Quality Notes

- **FMP Earnings Calendar:** Generally reliable but check for missing/incorrect times
- **Alpaca Intraday Bars:** IEX feed (free tier) - sufficient for research, not HFT
- **Manual Fallback:** Script includes curated MU earnings list if FMP fails
- **Missing Data Handling:** Tickers with no data on event date are excluded (logged)

---

## Governance Compliance

✅ **STUDY_EXECUTION_PROTOCOL.md:** Followed  
✅ **LAB_READY_CHECK.md:** Implemented (Step 0)  
✅ **API_MAP.md:** Alpaca-first routing (intraday + daily)  
✅ **No parameter optimization:** All parameters in PARAMS block  
✅ **No hard-coded price levels:** All metrics ATR-normalized  
✅ **Deterministic execution:** Fixed random seeds not needed (no randomness)  
✅ **Reproducible:** Same inputs = same outputs (API data permitting)

---

**Study Status:** ✅ Ready for Execution  
**Last Updated:** December 16, 2025  
**Python:** 3.13.5  
**Author:** Head of Quant Strategy (AI Agent)
