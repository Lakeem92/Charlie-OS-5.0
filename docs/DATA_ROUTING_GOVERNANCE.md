"""
Data Routing Governance - Provider Defaults by Study Type
==========================================================

This document confirms the default data provider for each study type
after implementing the API_MAP.md governance rules.

GOVERNANCE RULE:
All volatility, TTP, indicator evaluation, honesty tests, and return 
calculations MUST use Alpaca price data by default unless explicitly overridden.

Provider Defaults by Study Type
--------------------------------

ALPACA REQUIRED (study_type parameter enforces Alpaca):
  ✓ volatility           → Alpaca (ensures consistent regime calculations)
  ✓ returns              → Alpaca (forward returns, holding period analysis)
  ✓ indicator            → Alpaca (indicator edge detection, signal evaluation)
  ✓ honesty_test         → Alpaca (behavioral separation tests)
  ✓ ttp                  → Alpaca (time-to-profit studies)

FLEXIBLE (yfinance default, can use any source):
  • exploratory          → yfinance (quick checks, idea testing)
  • screening            → yfinance (multi-ticker scans)
  • backtesting          → Alpaca recommended, but flexible
  • event_study          → Source depends on data availability
  • general              → yfinance (default for unspecified studies)

INDICES & PROXIES (yfinance only):
  • ^VIX, ^SPX, ^MOVE    → yfinance (not available on Alpaca)
  • Non-US equities      → yfinance (not on US exchanges)

Usage Examples
--------------

1. Indicator Honesty Test (auto-routes to Alpaca):
   ```python
   df = DataRouter.get_price_data(
       ticker='TSLA',
       start_date='2023-01-01',
       study_type='honesty_test'  # ← Forces Alpaca
   )
   ```

2. Forward Returns Study (auto-routes to Alpaca):
   ```python
   df = DataRouter.get_price_data(
       ticker='BABA',
       start_date='2024-01-01',
       study_type='returns'  # ← Forces Alpaca
   )
   ```

3. Override Warning (logs warning, allows yfinance):
   ```python
   df = DataRouter.get_price_data(
       ticker='TSLA',
       start_date='2024-01-01',
       source='yfinance',          # ← Explicit override
       study_type='returns'         # ← Triggers warning
   )
   # Logs: "⚠️ GOVERNANCE WARNING: Study type 'returns' requires Alpaca..."
   ```

4. Exploratory Work (yfinance default):
   ```python
   df = DataRouter.get_price_data(
       ticker='TSLA',
       start_date='2024-01-01'
       # No study_type = uses yfinance default
   )
   ```

Warning System
--------------

When yfinance is explicitly used for Alpaca-required study types:

  ⚠️  GOVERNANCE WARNING: Study type 'returns' requires Alpaca data 
  by default per API_MAP.md. Using yfinance may introduce vendor 
  discrepancies in forward returns and execution alignment. 
  Reason: Explicitly overridden with source='yfinance'

This warning ensures users are aware they're deviating from the 
governance standard and understand the potential implications.

Benefits of This Governance
----------------------------

✓ Consistent Price Source:
  - No vendor discrepancies across studies
  - Same data for analysis and future execution
  
✓ Reproducible Results:
  - Forward returns match what you'll see in paper/live trading
  - No "backtest looks great but live fails" surprises
  
✓ Transparent Overrides:
  - Clear warnings when deviating from standards
  - Explicit reasoning required for exceptions
  
✓ Flexible Where Needed:
  - Exploratory work still uses fast yfinance
  - Indices and non-US symbols supported
  - Easy to override when necessary

Implementation Status
---------------------

✅ API_MAP.md updated with governance rules
✅ data_router.py implements study_type enforcement
✅ Warning guard logs yfinance overrides
✅ Backwards compatible (no breaking changes)
✅ Environment loading fixed (Alpaca credentials working)

Next Steps
----------

When creating new studies:
1. Always specify study_type parameter for production work
2. Use 'returns', 'indicator', 'honesty_test', etc. for analytical studies
3. Let the router handle source selection automatically
4. Only override source when symbol is unavailable on Alpaca

Last Updated: December 14, 2025
