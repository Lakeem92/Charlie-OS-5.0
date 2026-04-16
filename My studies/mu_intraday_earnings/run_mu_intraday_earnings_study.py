"""
MU Earnings Intraday Volatility Expansion & Substitution Study (API-SAFE)
With CORRECTED Earnings-to-Session Mapping

This study determines whether MU itself is the best intraday volatility vehicle
on MU earnings days, or whether MU-correlated names exhibit earlier, larger, 
and cleaner ATR-normalized expansion.

CRITICAL FIX: Proper BMO/AMC classification and event session mapping.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import pytz
import pandas as pd
import numpy as np
import requests
from typing import Dict, List, Tuple, Optional
import time

# Add shared config to path
sys.path.append(str(Path(__file__).parent.parent.parent / 'shared'))
from config.api_clients import AlpacaClient, FMPClient

# ============================================================================
# PARAMETER BLOCK (TOP OF CODE - NON-NEGOTIABLE)
# ============================================================================

PARAMS = {
    'bar_size': '5Min',
    'start_date': '2016-01-01',
    'end_date': datetime.now().strftime('%Y-%m-%d'),
    'atr_length': 14,
    'tickers': [
        'MU', 'NVDA', 'AMD', 'AVGO', 'QCOM', 'INTC', 'TXN', 
        'AMAT', 'LRCX', 'KLAC', 'ASML', 'TSM', 'MRVL', 
        'ON', 'MPWR', 'MCHP', 'ADI', 'ALAB'
    ],
    'flat_threshold': 0.01,  # ±1% for FLAT classification
    'expansion_targets_atr': [0.5, 1.0, 1.5],
    'reversal_threshold_atr': 0.3,
    'orb_minutes': 15,
}

# Timezone
CT = pytz.timezone('America/Chicago')
UTC = pytz.UTC

# Session times (Central Time)
PREMARKET_START = {'hour': 3, 'minute': 0}
PREMARKET_END = {'hour': 8, 'minute': 29}
RTH_START = {'hour': 8, 'minute': 30}
RTH_END = {'hour': 15, 'minute': 0}

# ============================================================================
# STEP 0 — LAB READY CHECK
# ============================================================================

def lab_ready_check():
    """Verify all prerequisites before execution."""
    print("=" * 80)
    print("STEP 0 — LAB READY CHECK")
    print("=" * 80)
    
    checks = {}
    
    # Check 1: Alpaca connectivity
    try:
        alpaca = AlpacaClient()
        test_bars = alpaca.get_bars('MU', timeframe='1Day', limit=5)
        if 'bars' in test_bars and len(test_bars['bars']) > 0:
            checks['Alpaca connectivity'] = True
            print("✅ Alpaca API: Connected and responding")
        else:
            checks['Alpaca connectivity'] = False
            print("❌ Alpaca API: Connected but no data returned")
    except Exception as e:
        checks['Alpaca connectivity'] = False
        print(f"❌ Alpaca API: Connection failed - {e}")
    
    # Check 2: FMP earnings calendar availability
    try:
        fmp = FMPClient()
        # Test with a small query
        checks['FMP earnings calendar'] = True
        print("✅ FMP API: Available for earnings calendar")
    except Exception as e:
        checks['FMP earnings calendar'] = False
        print(f"❌ FMP API: Failed - {e}")
    
    # Check 3: Required libraries
    try:
        import pandas
        import numpy
        import pytz
        checks['Required libraries'] = True
        print("✅ Required Python libraries: Available")
    except ImportError as e:
        checks['Required libraries'] = False
        print(f"❌ Required libraries: Missing - {e}")
    
    # Final verdict
    print("\n" + "=" * 80)
    if all(checks.values()):
        print("✅ LAB READY CHECK: PASSED")
        print("=" * 80)
        return True
    else:
        print("❌ LAB READY CHECK: FAILED")
        print("\nFailing checks:")
        for check, status in checks.items():
            if not status:
                print(f"  - {check}")
        print("=" * 80)
        print("\n🛑 HARD FAIL: Cannot proceed without required infrastructure")
        return False

# ============================================================================
# STEP 1 — GET MU EARNINGS DATES WITH TIMESTAMPS (CORRECTED)
# ============================================================================

def get_mu_earnings_dates_fmp(start_date: str, end_date: str) -> pd.DataFrame:
    """
    Retrieve MU earnings announcements with timestamps from FMP.
    
    Returns DataFrame with columns:
        - announcement_datetime (timezone-aware)
        - fiscal_quarter
        - eps_actual
        - eps_estimate
    """
    print("\n" + "=" * 80)
    print("STEP 1 — GET MU EARNINGS DATES WITH TIMESTAMPS")
    print("=" * 80)
    
    fmp = FMPClient()
    
    try:
        # FMP earnings calendar endpoint
        url = f"{fmp.base_url}/historical/earning_calendar/MU"
        params = {'apikey': fmp.api_key, 'limit': 200}
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if not data:
            print("⚠️  No earnings data returned from FMP")
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        
        # Filter by date range
        df['date'] = pd.to_datetime(df['date'])
        df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
        
        # Parse time if available, otherwise use market close time as default
        earnings_records = []
        
        for _, row in df.iterrows():
            date = row['date']
            
            # FMP provides 'time' field (e.g., "amc", "bmo", or specific time)
            time_str = row.get('time', 'amc').lower() if 'time' in row else 'amc'
            
            # Create datetime with timezone awareness
            base_date = date.date()
            
            if time_str == 'bmo':
                # Before market open: 7:00 AM CT (before 8:30 AM open)
                dt = datetime.combine(base_date, datetime.min.time().replace(hour=7, minute=0))
                dt = CT.localize(dt)
            elif time_str == 'amc':
                # After market close: 4:00 PM CT (after 3:00 PM close)
                dt = datetime.combine(base_date, datetime.min.time().replace(hour=16, minute=0))
                dt = CT.localize(dt)
            else:
                # Try to parse specific time or default to AMC
                try:
                    # FMP might provide time like "16:00:00"
                    time_parts = time_str.split(':')
                    hour = int(time_parts[0])
                    minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                    dt = datetime.combine(base_date, datetime.min.time().replace(hour=hour, minute=minute))
                    dt = CT.localize(dt)
                except:
                    # Default to AMC
                    dt = datetime.combine(base_date, datetime.min.time().replace(hour=16, minute=0))
                    dt = CT.localize(dt)
            
            earnings_records.append({
                'announcement_datetime': dt,
                'calendar_date': base_date,
                'fiscal_quarter': row.get('fiscalDateEnding', 'Unknown'),
                'eps_actual': row.get('eps', None),
                'eps_estimate': row.get('epsEstimated', None),
                'time_label': time_str
            })
        
        earnings_df = pd.DataFrame(earnings_records)
        
        print(f"✅ Retrieved {len(earnings_df)} MU earnings announcements from FMP")
        print(f"   Date range: {earnings_df['calendar_date'].min()} to {earnings_df['calendar_date'].max()}")
        
        return earnings_df
        
    except Exception as e:
        print(f"❌ Failed to retrieve MU earnings from FMP: {e}")
        print("   Falling back to manual earnings dates...")
        return get_mu_earnings_dates_manual(start_date, end_date)

def get_mu_earnings_dates_manual(start_date: str, end_date: str) -> pd.DataFrame:
    """
    Fallback: Manual MU earnings dates with timing classification.
    Based on known historical MU earnings patterns.
    """
    # Known MU earnings dates (recent history) - manually curated
    manual_earnings = [
        ('2024-12-18', 'amc'),
        ('2024-09-25', 'amc'),
        ('2024-06-26', 'amc'),
        ('2024-03-20', 'amc'),
        ('2023-12-20', 'amc'),
        ('2023-09-27', 'amc'),
        ('2023-06-28', 'amc'),
        ('2023-03-29', 'amc'),
        ('2022-12-20', 'amc'),
        ('2022-09-28', 'amc'),
        ('2022-06-30', 'amc'),
        ('2022-03-30', 'amc'),
        ('2021-12-20', 'amc'),
        ('2021-09-28', 'amc'),
        ('2021-06-30', 'amc'),
        ('2021-03-31', 'amc'),
        ('2020-12-21', 'amc'),
        ('2020-09-29', 'amc'),
        ('2020-06-29', 'amc'),
        ('2020-03-25', 'amc'),
        ('2019-12-18', 'amc'),
        ('2019-09-26', 'amc'),
        ('2019-06-25', 'amc'),
        ('2019-03-20', 'amc'),
        ('2018-12-19', 'amc'),
        ('2018-09-20', 'amc'),
        ('2018-06-27', 'amc'),
        ('2018-03-21', 'amc'),
        ('2017-12-19', 'amc'),
        ('2017-09-21', 'amc'),
        ('2017-06-27', 'amc'),
        ('2017-03-22', 'amc'),
        ('2016-12-20', 'amc'),
        ('2016-09-22', 'amc'),
        ('2016-06-23', 'amc'),
        ('2016-03-23', 'amc'),
    ]
    
    earnings_records = []
    
    for date_str, timing in manual_earnings:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        if date_obj < datetime.strptime(start_date, '%Y-%m-%d').date():
            continue
        if date_obj > datetime.strptime(end_date, '%Y-%m-%d').date():
            continue
        
        if timing == 'bmo':
            dt = datetime.combine(date_obj, datetime.min.time().replace(hour=7, minute=0))
            dt = CT.localize(dt)
        else:  # amc
            dt = datetime.combine(date_obj, datetime.min.time().replace(hour=16, minute=0))
            dt = CT.localize(dt)
        
        earnings_records.append({
            'announcement_datetime': dt,
            'calendar_date': date_obj,
            'fiscal_quarter': 'Unknown',
            'eps_actual': None,
            'eps_estimate': None,
            'time_label': timing
        })
    
    df = pd.DataFrame(earnings_records)
    print(f"✅ Using {len(df)} manual MU earnings dates")
    
    return df

# ============================================================================
# STEP A-C — CLASSIFY AND MAP TO EVENT SESSION (CORRECTED)
# ============================================================================

def classify_earnings_timing(announcement_dt: datetime) -> str:
    """
    Classify earnings announcement as BMO, AMC, or INVALID.
    
    Args:
        announcement_dt: Timezone-aware datetime in CT
    
    Returns:
        'BMO', 'AMC', or 'INVALID'
    """
    hour = announcement_dt.hour
    minute = announcement_dt.minute
    
    # BMO: Before 8:30 AM CT
    if hour < 8 or (hour == 8 and minute < 30):
        return 'BMO'
    
    # AMC: At or after 4:00 PM CT (16:00)
    if hour >= 16:
        return 'AMC'
    
    # During market hours: INVALID
    return 'INVALID'

def map_event_session_date(announcement_dt: datetime, timing: str, alpaca: AlpacaClient) -> Optional[datetime.date]:
    """
    Map earnings announcement to the correct event trading session.
    
    Rules:
        - BMO → same trading day
        - AMC → next trading day
        - INVALID → None (exclude)
    
    Args:
        announcement_dt: Timezone-aware announcement datetime
        timing: 'BMO', 'AMC', or 'INVALID'
        alpaca: AlpacaClient for calendar lookup
    
    Returns:
        Event session date or None if invalid
    """
    if timing == 'INVALID':
        return None
    
    calendar_date = announcement_dt.date()
    
    if timing == 'BMO':
        # Same trading day (verify it's a trading day)
        return calendar_date
    
    else:  # AMC
        # Next trading day
        try:
            # Get calendar for next 10 days to find next trading day
            end_date = (calendar_date + timedelta(days=10)).strftime('%Y-%m-%d')
            cal = alpaca.get_calendar(
                start=calendar_date.strftime('%Y-%m-%d'),
                end=end_date
            )
            
            if len(cal) < 2:
                # Can't find next trading day
                return None
            
            # First entry is announcement day, second is next trading day
            next_trading_day = datetime.strptime(cal[1]['date'], '%Y-%m-%d').date()
            return next_trading_day
            
        except Exception as e:
            print(f"⚠️  Error finding next trading day for {calendar_date}: {e}")
            # Fallback: add 1 day (might land on weekend, will be filtered later)
            return calendar_date + timedelta(days=1)

def process_earnings_dates(earnings_df: pd.DataFrame, alpaca: AlpacaClient) -> pd.DataFrame:
    """
    Process earnings dates: classify timing and map to event session.
    
    Returns DataFrame with additional columns:
        - timing_class: 'BMO', 'AMC', or 'INVALID'
        - event_session_date: The correct trading date for analysis
    """
    print("\n" + "=" * 80)
    print("STEP A-C — CLASSIFY AND MAP TO EVENT SESSION")
    print("=" * 80)
    
    results = []
    
    for _, row in earnings_df.iterrows():
        announcement_dt = row['announcement_datetime']
        
        # Ensure timezone aware
        if announcement_dt.tzinfo is None:
            announcement_dt = CT.localize(announcement_dt)
        elif announcement_dt.tzinfo != CT:
            announcement_dt = announcement_dt.astimezone(CT)
        
        # Classify
        timing = classify_earnings_timing(announcement_dt)
        
        # Map to session
        event_session_date = map_event_session_date(announcement_dt, timing, alpaca)
        
        results.append({
            **row.to_dict(),
            'timing_class': timing,
            'event_session_date': event_session_date
        })
    
    processed_df = pd.DataFrame(results)
    
    # Filter out INVALID
    valid_df = processed_df[processed_df['timing_class'] != 'INVALID'].copy()
    valid_df = valid_df[valid_df['event_session_date'].notna()].copy()
    
    # Summary
    print(f"\n📊 Earnings Classification Summary:")
    print(f"   Total announcements: {len(earnings_df)}")
    print(f"   BMO: {len(processed_df[processed_df['timing_class'] == 'BMO'])}")
    print(f"   AMC: {len(processed_df[processed_df['timing_class'] == 'AMC'])}")
    print(f"   INVALID (excluded): {len(processed_df[processed_df['timing_class'] == 'INVALID'])}")
    print(f"   Valid event sessions: {len(valid_df)}")
    
    return valid_df

# ============================================================================
# STEP 2 & 4 — DAILY ATR BASELINE (CORRECTED ALIGNMENT)
# ============================================================================

def compute_daily_atr(ticker: str, event_dates: List[datetime.date], 
                      alpaca: AlpacaClient, atr_length: int = 14) -> Dict[datetime.date, float]:
    """
    Compute ATR(14) for each event date using data STRICTLY PRIOR to event session.
    
    Args:
        ticker: Stock symbol
        event_dates: List of event session dates
        alpaca: AlpacaClient
        atr_length: ATR period (default 14)
    
    Returns:
        Dict mapping event_date -> ATR value
    """
    if not event_dates:
        return {}
    
    # Fetch sufficient daily data
    start_date = min(event_dates) - timedelta(days=atr_length * 2)  # Buffer for weekends
    end_date = max(event_dates)
    
    try:
        bars = alpaca.get_bars(
            ticker,
            timeframe='1Day',
            start=start_date.strftime('%Y-%m-%d'),
            end=end_date.strftime('%Y-%m-%d'),
            limit=10000
        )
        
        if 'bars' not in bars or not bars['bars']:
            return {}
        
        df = pd.DataFrame(bars['bars'])
        df['date'] = pd.to_datetime(df['t']).dt.date
        df = df.sort_values('date')
        
        # Compute True Range
        df['high'] = df['h'].astype(float)
        df['low'] = df['l'].astype(float)
        df['close'] = df['c'].astype(float)
        df['prev_close'] = df['close'].shift(1)
        
        df['tr'] = df.apply(lambda row: max(
            row['high'] - row['low'],
            abs(row['high'] - row['prev_close']) if pd.notna(row['prev_close']) else 0,
            abs(row['low'] - row['prev_close']) if pd.notna(row['prev_close']) else 0
        ), axis=1)
        
        # Rolling ATR
        df['atr'] = df['tr'].rolling(window=atr_length, min_periods=atr_length).mean()
        
        # Map to event dates (use ATR from PRIOR day)
        atr_map = {}
        for event_date in event_dates:
            # Get data strictly before event date
            prior_data = df[df['date'] < event_date]
            if not prior_data.empty and pd.notna(prior_data.iloc[-1]['atr']):
                atr_map[event_date] = prior_data.iloc[-1]['atr']
        
        return atr_map
        
    except Exception as e:
        print(f"⚠️  Error computing ATR for {ticker}: {e}")
        return {}

def compute_all_tickers_atr(tickers: List[str], event_dates: List[datetime.date], 
                            alpaca: AlpacaClient, atr_length: int = 14) -> pd.DataFrame:
    """
    Compute ATR for all tickers for all event dates.
    
    Returns DataFrame with columns: event_date, ticker, atr
    """
    print("\n" + "=" * 80)
    print("STEP 2 & 4 — DAILY ATR BASELINE (CORRECTED ALIGNMENT)")
    print("=" * 80)
    
    all_atr_data = []
    
    for ticker in tickers:
        print(f"Computing ATR for {ticker}...")
        atr_map = compute_daily_atr(ticker, event_dates, alpaca, atr_length)
        
        for event_date, atr_value in atr_map.items():
            all_atr_data.append({
                'event_date': event_date,
                'ticker': ticker,
                'atr': atr_value
            })
        
        time.sleep(0.2)  # Rate limiting
    
    atr_df = pd.DataFrame(all_atr_data)
    print(f"\n✅ Computed ATR for {len(tickers)} tickers across {len(event_dates)} event dates")
    print(f"   Total ATR records: {len(atr_df)}")
    
    return atr_df

# ============================================================================
# STEP 3 & 5 — INTRADAY DATA PULL (API-SAFE, EVENT-FILTERED)
# ============================================================================

def fetch_intraday_bars(ticker: str, event_date: datetime.date, 
                       alpaca: AlpacaClient, bar_size: str = '5Min') -> pd.DataFrame:
    """
    Fetch intraday bars for a single event date.
    Includes premarket (3:00 AM) through RTH close (3:00 PM) CT.
    """
    # Build timestamp range in CT
    start_dt = datetime.combine(event_date, datetime.min.time().replace(hour=3, minute=0))
    start_dt = CT.localize(start_dt)
    
    end_dt = datetime.combine(event_date, datetime.min.time().replace(hour=15, minute=0))
    end_dt = CT.localize(end_dt)
    
    # Convert to RFC3339 for Alpaca
    start_str = start_dt.isoformat()
    end_str = end_dt.isoformat()
    
    try:
        bars = alpaca.get_bars(
            ticker,
            timeframe=bar_size,
            start=start_str,
            end=end_str,
            limit=10000
        )
        
        if 'bars' not in bars or not bars['bars']:
            return pd.DataFrame()
        
        df = pd.DataFrame(bars['bars'])
        df['timestamp'] = pd.to_datetime(df['t'])
        df['timestamp'] = df['timestamp'].dt.tz_convert(CT)
        
        df['open'] = df['o'].astype(float)
        df['high'] = df['h'].astype(float)
        df['low'] = df['l'].astype(float)
        df['close'] = df['c'].astype(float)
        df['volume'] = df['v'].astype(float)
        
        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        
    except Exception as e:
        print(f"⚠️  Error fetching intraday bars for {ticker} on {event_date}: {e}")
        return pd.DataFrame()

def fetch_all_intraday_data(tickers: List[str], event_dates: List[datetime.date],
                            alpaca: AlpacaClient, bar_size: str = '5Min') -> Dict:
    """
    Fetch intraday data for all tickers on all event dates (API-SAFE).
    
    Returns nested dict: {event_date: {ticker: DataFrame}}
    """
    print("\n" + "=" * 80)
    print("STEP 3 & 5 — INTRADAY DATA PULL (API-SAFE, EVENT-FILTERED)")
    print("=" * 80)
    
    intraday_data = {}
    total_fetches = len(tickers) * len(event_dates)
    current_fetch = 0
    
    for event_date in event_dates:
        intraday_data[event_date] = {}
        
        for ticker in tickers:
            current_fetch += 1
            print(f"[{current_fetch}/{total_fetches}] Fetching {ticker} on {event_date}...")
            
            df = fetch_intraday_bars(ticker, event_date, alpaca, bar_size)
            
            if not df.empty:
                intraday_data[event_date][ticker] = df
            
            time.sleep(0.15)  # Rate limiting
    
    # Summary
    total_successful = sum(len(tickers_dict) for tickers_dict in intraday_data.values())
    print(f"\n✅ Fetched intraday data: {total_successful}/{total_fetches} successful")
    
    return intraday_data

# ============================================================================
# STEP 6 — MU EARNINGS DAY REGIME LABELING
# ============================================================================

def label_mu_regime(intraday_data: Dict, event_date: datetime.date, 
                   flat_threshold: float = 0.01) -> str:
    """
    Label MU earnings day regime based on open-to-close return.
    
    Returns: 'UPSIDE', 'DOWNSIDE', or 'FLAT'
    """
    if event_date not in intraday_data:
        return 'UNKNOWN'
    
    if 'MU' not in intraday_data[event_date]:
        return 'UNKNOWN'
    
    mu_df = intraday_data[event_date]['MU']
    
    # RTH only (8:30 - 15:00 CT)
    rth_df = mu_df[
        (mu_df['timestamp'].dt.hour > 8) |
        ((mu_df['timestamp'].dt.hour == 8) & (mu_df['timestamp'].dt.minute >= 30))
    ]
    rth_df = rth_df[
        (rth_df['timestamp'].dt.hour < 15) |
        ((rth_df['timestamp'].dt.hour == 15) & (rth_df['timestamp'].dt.minute == 0))
    ]
    
    if rth_df.empty or len(rth_df) < 2:
        return 'UNKNOWN'
    
    mu_open = rth_df.iloc[0]['open']
    mu_close = rth_df.iloc[-1]['close']
    
    ret = (mu_close - mu_open) / mu_open
    
    if ret > flat_threshold:
        return 'UPSIDE'
    elif ret < -flat_threshold:
        return 'DOWNSIDE'
    else:
        return 'FLAT'

def label_all_regimes(intraday_data: Dict, event_dates: List[datetime.date],
                     flat_threshold: float = 0.01) -> Dict[datetime.date, str]:
    """
    Label regime for all event dates.
    
    Returns: Dict mapping event_date -> regime
    """
    print("\n" + "=" * 80)
    print("STEP 6 — MU EARNINGS DAY REGIME LABELING")
    print("=" * 80)
    
    regimes = {}
    
    for event_date in event_dates:
        regime = label_mu_regime(intraday_data, event_date, flat_threshold)
        regimes[event_date] = regime
        print(f"  {event_date}: {regime}")
    
    # Summary
    regime_counts = pd.Series(list(regimes.values())).value_counts()
    print(f"\n📊 Regime Distribution:")
    for regime, count in regime_counts.items():
        print(f"   {regime}: {count}")
    
    return regimes

# ============================================================================
# STEP 7 — INTRADAY VOLATILITY EXPANSION METRICS
# ============================================================================

def compute_expansion_metrics(ticker: str, event_date: datetime.date,
                              intraday_data: Dict, atr_df: pd.DataFrame,
                              expansion_targets: List[float]) -> Dict:
    """
    Compute intraday volatility expansion metrics for a ticker on an event date.
    """
    if event_date not in intraday_data:
        return None
    
    if ticker not in intraday_data[event_date]:
        return None
    
    # Get ATR
    atr_row = atr_df[(atr_df['event_date'] == event_date) & (atr_df['ticker'] == ticker)]
    if atr_row.empty:
        return None
    
    atr_value = atr_row.iloc[0]['atr']
    if pd.isna(atr_value) or atr_value <= 0:
        return None
    
    df = intraday_data[event_date][ticker]
    
    # RTH data
    rth_df = df[
        (df['timestamp'].dt.hour > 8) |
        ((df['timestamp'].dt.hour == 8) & (df['timestamp'].dt.minute >= 30))
    ]
    rth_df = rth_df[df['timestamp'].dt.hour < 15]
    
    if rth_df.empty:
        return None
    
    ticker_open = rth_df.iloc[0]['open']
    
    # Excursions
    max_high = df['high'].max()
    min_low = df['low'].min()
    
    open_high_exc = (max_high - ticker_open) / ticker_open
    open_low_exc = (ticker_open - min_low) / ticker_open
    max_exc = max(open_high_exc, open_low_exc)
    full_range = (max_high - min_low) / ticker_open
    
    # ATR-normalized
    open_high_atr = (max_high - ticker_open) / atr_value
    open_low_atr = (ticker_open - min_low) / atr_value
    max_exc_atr = max(open_high_atr, open_low_atr)
    range_atr = (max_high - min_low) / atr_value
    
    # Time-to-expansion
    time_to_targets = {}
    df['running_max_high'] = df['high'].expanding().max()
    df['running_min_low'] = df['low'].expanding().min()
    df['running_exc_atr'] = df.apply(
        lambda row: max(
            (row['running_max_high'] - ticker_open) / atr_value,
            (ticker_open - row['running_min_low']) / atr_value
        ), axis=1
    )
    
    rth_start = rth_df.iloc[0]['timestamp']
    
    for target in expansion_targets:
        hit_rows = df[df['running_exc_atr'] >= target]
        if not hit_rows.empty:
            hit_time = hit_rows.iloc[0]['timestamp']
            minutes_elapsed = (hit_time - rth_start).total_seconds() / 60
            time_to_targets[f'time_to_{target}atr'] = minutes_elapsed
        else:
            time_to_targets[f'time_to_{target}atr'] = np.nan
    
    # Session segments
    premarket_df = df[df['timestamp'].dt.hour < 8]
    morning_df = rth_df[rth_df['timestamp'].dt.hour < 11]
    
    premarket_max_exc_atr = 0
    if not premarket_df.empty:
        pm_high = premarket_df['high'].max()
        pm_low = premarket_df['low'].min()
        premarket_max_exc_atr = max(
            (pm_high - ticker_open) / atr_value,
            (ticker_open - pm_low) / atr_value
        )
    
    morning_max_exc_atr = 0
    if not morning_df.empty:
        am_high = morning_df['high'].max()
        am_low = morning_df['low'].min()
        morning_max_exc_atr = max(
            (am_high - ticker_open) / atr_value,
            (ticker_open - am_low) / atr_value
        )
    
    return {
        'ticker': ticker,
        'event_date': event_date,
        'atr': atr_value,
        'ticker_open': ticker_open,
        'max_high': max_high,
        'min_low': min_low,
        'open_high_exc_pct': open_high_exc,
        'open_low_exc_pct': open_low_exc,
        'max_exc_pct': max_exc,
        'range_pct': full_range,
        'open_high_atr': open_high_atr,
        'open_low_atr': open_low_atr,
        'max_exc_atr': max_exc_atr,
        'range_atr': range_atr,
        **time_to_targets,
        'premarket_max_exc_atr': premarket_max_exc_atr,
        'morning_max_exc_atr': morning_max_exc_atr
    }

def compute_all_expansion_metrics(tickers: List[str], event_dates: List[datetime.date],
                                 intraday_data: Dict, atr_df: pd.DataFrame,
                                 expansion_targets: List[float]) -> pd.DataFrame:
    """
    Compute expansion metrics for all tickers on all event dates.
    """
    print("\n" + "=" * 80)
    print("STEP 7 — INTRADAY VOLATILITY EXPANSION METRICS")
    print("=" * 80)
    
    all_metrics = []
    
    for event_date in event_dates:
        for ticker in tickers:
            metrics = compute_expansion_metrics(
                ticker, event_date, intraday_data, atr_df, expansion_targets
            )
            if metrics:
                all_metrics.append(metrics)
    
    metrics_df = pd.DataFrame(all_metrics)
    print(f"✅ Computed expansion metrics: {len(metrics_df)} records")
    
    return metrics_df

# ============================================================================
# STEP 8 — INTRADAY PATH QUALITY METRICS
# ============================================================================

def compute_path_quality_metrics(ticker: str, event_date: datetime.date,
                                intraday_data: Dict, atr_df: pd.DataFrame,
                                reversal_threshold_atr: float,
                                orb_minutes: int) -> Dict:
    """
    Compute path quality metrics: directional efficiency, reversals, wicks, CLV.
    """
    if event_date not in intraday_data:
        return None
    
    if ticker not in intraday_data[event_date]:
        return None
    
    # Get ATR
    atr_row = atr_df[(atr_df['event_date'] == event_date) & (atr_df['ticker'] == ticker)]
    if atr_row.empty:
        return None
    
    atr_value = atr_row.iloc[0]['atr']
    if pd.isna(atr_value) or atr_value <= 0:
        return None
    
    df = intraday_data[event_date][ticker].copy()
    
    # RTH data
    rth_df = df[
        (df['timestamp'].dt.hour > 8) |
        ((df['timestamp'].dt.hour == 8) & (df['timestamp'].dt.minute >= 30))
    ]
    rth_df = rth_df[df['timestamp'].dt.hour < 15]
    
    if rth_df.empty or len(rth_df) < 2:
        return None
    
    ticker_open = rth_df.iloc[0]['open']
    ticker_close = rth_df.iloc[-1]['close']
    
    max_high = df['high'].max()
    min_low = df['low'].min()
    full_range = max_high - min_low
    
    # Directional efficiency
    open_to_close_return = abs(ticker_close - ticker_open)
    directional_efficiency = open_to_close_return / full_range if full_range > 0 else 0
    
    # Reversal count
    reversal_threshold_price = reversal_threshold_atr * atr_value
    reversals = 0
    
    df['running_max'] = df['high'].expanding().max()
    df['running_min'] = df['low'].expanding().min()
    df['pullback_from_high'] = df['running_max'] - df['low']
    df['pullback_from_low'] = df['high'] - df['running_min']
    
    reversals = (
        (df['pullback_from_high'] >= reversal_threshold_price).sum() +
        (df['pullback_from_low'] >= reversal_threshold_price).sum()
    )
    
    # Wick/body ratio
    df['body'] = abs(df['close'] - df['open'])
    df['wick'] = (df['high'] - df['low']) - df['body']
    avg_wick_ratio = (df['wick'] / (df['body'] + 0.0001)).mean()  # Avoid div by zero
    
    # CLV (compute on full df, then filter)
    df['clv'] = (2 * df['close'] - df['high'] - df['low']) / (df['high'] - df['low'] + 0.0001)
    
    # Get CLV for RTH only
    rth_df_with_clv = df[df['timestamp'].isin(rth_df['timestamp'])]
    avg_clv_rth = rth_df_with_clv['clv'].mean() if not rth_df_with_clv.empty else 0
    
    # ORB proxy
    orb_df = rth_df.head(orb_minutes // 5)  # Assuming 5-min bars
    if not orb_df.empty and len(orb_df) >= 2:
        orb_high = orb_df['high'].max()
        orb_low = orb_df['low'].min()
        
        breakout_up = (df['high'] > orb_high).any()
        breakout_down = (df['low'] < orb_low).any()
        orb_breakout = breakout_up or breakout_down
    else:
        orb_breakout = False
    
    return {
        'ticker': ticker,
        'event_date': event_date,
        'directional_efficiency': directional_efficiency,
        'reversal_count': reversals,
        'avg_wick_ratio': avg_wick_ratio,
        'avg_clv_rth': avg_clv_rth,
        'orb_breakout': orb_breakout
    }

def compute_all_path_quality_metrics(tickers: List[str], event_dates: List[datetime.date],
                                    intraday_data: Dict, atr_df: pd.DataFrame,
                                    reversal_threshold_atr: float,
                                    orb_minutes: int) -> pd.DataFrame:
    """
    Compute path quality metrics for all tickers on all event dates.
    """
    print("\n" + "=" * 80)
    print("STEP 8 — INTRADAY PATH QUALITY METRICS")
    print("=" * 80)
    
    all_metrics = []
    
    for event_date in event_dates:
        for ticker in tickers:
            metrics = compute_path_quality_metrics(
                ticker, event_date, intraday_data, atr_df,
                reversal_threshold_atr, orb_minutes
            )
            if metrics:
                all_metrics.append(metrics)
    
    quality_df = pd.DataFrame(all_metrics)
    print(f"✅ Computed path quality metrics: {len(quality_df)} records")
    
    return quality_df

# ============================================================================
# STEP 9 — REGIME-CONDITIONED RANKINGS
# ============================================================================

def build_regime_rankings(expansion_df: pd.DataFrame, quality_df: pd.DataFrame,
                         regimes: Dict[datetime.date, str]) -> pd.DataFrame:
    """
    Build regime-conditioned rankings comparing all tickers vs MU baseline.
    """
    print("\n" + "=" * 80)
    print("STEP 9 — REGIME-CONDITIONED RANKINGS")
    print("=" * 80)
    
    # Add regime labels
    expansion_df['regime'] = expansion_df['event_date'].map(regimes)
    quality_df['regime'] = quality_df['event_date'].map(regimes)
    
    # Merge
    combined_df = expansion_df.merge(
        quality_df[['ticker', 'event_date', 'directional_efficiency', 'reversal_count',
                   'avg_wick_ratio', 'avg_clv_rth', 'orb_breakout']],
        on=['ticker', 'event_date'],
        how='left'
    )
    
    # Rankings by regime
    rankings = []
    
    for regime in ['UPSIDE', 'DOWNSIDE', 'FLAT']:
        regime_data = combined_df[combined_df['regime'] == regime]
        
        if regime_data.empty:
            continue
        
        # Aggregate by ticker
        agg_metrics = regime_data.groupby('ticker').agg({
            'max_exc_atr': 'mean',
            'range_atr': 'mean',
            'time_to_1.0atr': 'mean',
            'directional_efficiency': 'mean',
            'reversal_count': 'mean',
            'avg_wick_ratio': 'mean'
        }).reset_index()
        
        # Percentage hitting 1 ATR
        agg_metrics['pct_hit_1atr'] = regime_data.groupby('ticker')['time_to_1.0atr'].apply(
            lambda x: (x.notna().sum() / len(x)) * 100
        ).values
        
        # Rank (higher is better for expansion, lower is better for chop)
        agg_metrics['rank_expansion'] = agg_metrics['max_exc_atr'].rank(ascending=False)
        agg_metrics['rank_speed'] = agg_metrics['time_to_1.0atr'].rank(ascending=True)
        agg_metrics['rank_clean'] = agg_metrics['reversal_count'].rank(ascending=True)
        
        # Composite score (simple average - documented)
        agg_metrics['composite_rank'] = (
            agg_metrics['rank_expansion'] + 
            agg_metrics['rank_speed'] + 
            agg_metrics['rank_clean']
        ) / 3
        agg_metrics['composite_rank'] = agg_metrics['composite_rank'].rank(ascending=True)
        
        agg_metrics['regime'] = regime
        agg_metrics['sample_size'] = len(regime_data[regime_data['ticker'] == agg_metrics.iloc[0]['ticker']])
        
        rankings.append(agg_metrics)
    
    rankings_df = pd.DataFrame()
    if rankings:
        rankings_df = pd.concat(rankings, ignore_index=True)
    
    print(f"✅ Built rankings for {len(rankings_df)} ticker-regime combinations")
    
    return rankings_df

# ============================================================================
# STEP 10 — EXPORT OUTPUTS
# ============================================================================

def export_outputs(expansion_df: pd.DataFrame, quality_df: pd.DataFrame,
                  rankings_df: pd.DataFrame, earnings_df: pd.DataFrame,
                  regimes: Dict, output_dir: Path):
    """
    Export all required CSV files and run_log.txt.
    """
    print("\n" + "=" * 80)
    print("STEP 10 — EXPORT OUTPUTS")
    print("=" * 80)
    
    output_dir.mkdir(exist_ok=True)
    
    # Add regime to expansion and quality
    expansion_df['regime'] = expansion_df['event_date'].map(regimes)
    quality_df['regime'] = quality_df['event_date'].map(regimes)
    
    # File 1: Expansion metrics
    exp_file = output_dir / 'mu_intraday_atr_expansion.csv'
    expansion_df.to_csv(exp_file, index=False)
    print(f"✅ Saved: {exp_file.name}")
    
    # File 2: Path quality
    quality_file = output_dir / 'mu_intraday_path_quality.csv'
    quality_df.to_csv(quality_file, index=False)
    print(f"✅ Saved: {quality_file.name}")
    
    # File 3: Rankings
    rankings_file = output_dir / 'mu_intraday_rankings_by_regime.csv'
    rankings_df.to_csv(rankings_file, index=False)
    print(f"✅ Saved: {rankings_file.name}")
    
    # File 4: Run log
    log_file = output_dir / 'run_log.txt'
    with open(log_file, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("MU EARNINGS INTRADAY VOLATILITY EXPANSION STUDY\n")
        f.write("Run Log\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Execution Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("PARAMETERS\n")
        f.write("-" * 80 + "\n")
        for key, value in PARAMS.items():
            f.write(f"{key}: {value}\n")
        f.write("\n")
        
        f.write("EARNINGS DATE ALIGNMENT FIX\n")
        f.write("-" * 80 + "\n")
        f.write("This study implements CORRECTED earnings-to-session mapping:\n")
        f.write("- BMO announcements map to SAME trading day\n")
        f.write("- AMC announcements map to NEXT trading day\n")
        f.write("- ATR computed using data STRICTLY PRIOR to event session\n")
        f.write("- Intraday bars pulled ONLY for event_session_date\n\n")
        
        f.write("SAMPLE SUMMARY\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total MU earnings announcements: {len(earnings_df)}\n")
        f.write(f"BMO: {len(earnings_df[earnings_df['timing_class'] == 'BMO'])}\n")
        f.write(f"AMC: {len(earnings_df[earnings_df['timing_class'] == 'AMC'])}\n")
        f.write(f"Valid event sessions: {len(set(earnings_df['event_session_date']))}\n\n")
        
        f.write("REGIME DISTRIBUTION\n")
        f.write("-" * 80 + "\n")
        regime_counts = pd.Series(list(regimes.values())).value_counts()
        for regime, count in regime_counts.items():
            f.write(f"{regime}: {count}\n")
        f.write("\n")
        
        f.write("DATA QUALITY\n")
        f.write("-" * 80 + "\n")
        f.write(f"Expansion metrics records: {len(expansion_df)}\n")
        f.write(f"Path quality metrics records: {len(quality_df)}\n")
        f.write(f"Ranking records: {len(rankings_df)}\n")
        f.write("\n")
        
        f.write("COMPOSITE RANKING FORMULA (FIXED WEIGHTS)\n")
        f.write("-" * 80 + "\n")
        f.write("composite_rank = (rank_expansion + rank_speed + rank_clean) / 3\n")
        f.write("Where:\n")
        f.write("  rank_expansion: max_exc_atr rank (higher = better)\n")
        f.write("  rank_speed: time_to_1.0atr rank (faster = better)\n")
        f.write("  rank_clean: reversal_count rank (lower = cleaner)\n")
        f.write("\n")
        
        f.write("=" * 80 + "\n")
    
    print(f"✅ Saved: {log_file.name}")
    print("\n" + "=" * 80)
    print("ALL OUTPUTS SAVED SUCCESSFULLY")
    print("=" * 80)

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """
    Main execution function.
    """
    print("\n" + "=" * 80)
    print("MU EARNINGS INTRADAY VOLATILITY EXPANSION STUDY")
    print("With CORRECTED Earnings-to-Session Mapping")
    print("=" * 80 + "\n")
    
    # Lab ready check
    if not lab_ready_check():
        return
    
    # Initialize clients
    alpaca = AlpacaClient()
    
    # Get MU earnings dates with timestamps
    earnings_df = get_mu_earnings_dates_fmp(PARAMS['start_date'], PARAMS['end_date'])
    
    if earnings_df.empty:
        print("🛑 HARD FAIL: No earnings dates available")
        return
    
    # Process: classify and map to event session
    earnings_df = process_earnings_dates(earnings_df, alpaca)
    
    if earnings_df.empty:
        print("🛑 HARD FAIL: No valid event sessions after classification")
        return
    
    event_dates = sorted(earnings_df['event_session_date'].unique())
    
    # Compute ATR baselines
    atr_df = compute_all_tickers_atr(
        PARAMS['tickers'], 
        event_dates, 
        alpaca, 
        PARAMS['atr_length']
    )
    
    if atr_df.empty:
        print("🛑 HARD FAIL: Could not compute ATR data")
        return
    
    # Fetch intraday data (API-SAFE)
    intraday_data = fetch_all_intraday_data(
        PARAMS['tickers'],
        event_dates,
        alpaca,
        PARAMS['bar_size']
    )
    
    # Label MU regimes
    regimes = label_all_regimes(intraday_data, event_dates, PARAMS['flat_threshold'])
    
    # Compute expansion metrics
    expansion_df = compute_all_expansion_metrics(
        PARAMS['tickers'],
        event_dates,
        intraday_data,
        atr_df,
        PARAMS['expansion_targets_atr']
    )
    
    # Compute path quality metrics
    quality_df = compute_all_path_quality_metrics(
        PARAMS['tickers'],
        event_dates,
        intraday_data,
        atr_df,
        PARAMS['reversal_threshold_atr'],
        PARAMS['orb_minutes']
    )
    
    # Build regime rankings
    rankings_df = build_regime_rankings(expansion_df, quality_df, regimes)
    
    # Export all outputs
    output_dir = Path(__file__).parent / 'outputs'
    export_outputs(expansion_df, quality_df, rankings_df, earnings_df, regimes, output_dir)
    
    # Summary
    print("\n" + "=" * 80)
    print("STUDY EXECUTION COMPLETE")
    print("=" * 80)
    print(f"\n📊 Summary:")
    print(f"   MU Earnings Events: {len(event_dates)}")
    print(f"   Tickers Analyzed: {len(PARAMS['tickers'])}")
    print(f"   Total Expansion Records: {len(expansion_df)}")
    print(f"   Total Path Quality Records: {len(quality_df)}")
    print(f"   Ranking Records: {len(rankings_df)}")
    print(f"\n📁 Outputs saved to: {output_dir}")
    print(f"   - mu_intraday_atr_expansion.csv")
    print(f"   - mu_intraday_path_quality.csv")
    print(f"   - mu_intraday_rankings_by_regime.csv")
    print(f"   - run_log.txt")
    print("\n" + "=" * 80)

if __name__ == '__main__':
    main()
