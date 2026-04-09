import sys
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
from shared.data_router import DataRouter
import pandas as pd

# Pick a ticker that we know has gap events (from the cache)
cache = pd.read_csv(r'C:\QuantLab\Data_Lab\studies\gap_execution_blueprint\outputs\gap_events_cache.csv')
print(f"Gap events: {len(cache)}")
print(f"Tickers: {cache['ticker'].unique()}")
print(f"\nFirst 5 events:")
print(cache[['ticker','date','gap_pct']].head(10))

# Pick first event
first = cache.iloc[0]
ticker = first['ticker']
date_str = first['date']
print(f"\nTesting ticker={ticker}, date={date_str}")

# Pull 5min data
intraday = DataRouter.get_price_data(ticker, '2024-01-01', end_date='2026-03-06', timeframe='5min')
print(f"\nIntraday rows: {len(intraday)}")
print(f"Index range: {intraday.index[0]} to {intraday.index[-1]}")

# Convert to Eastern
intraday.index = intraday.index.tz_convert('US/Eastern')
print(f"After tz_convert: {intraday.index[0]} to {intraday.index[-1]}")

# Try to match the event date
event_date = pd.Timestamp(date_str)
print(f"\nevent_date: {event_date}, type: {type(event_date)}")
print(f"event_date.date(): {event_date.date()}")

# Check what dates are in intraday
unique_dates = sorted(set(d.date() for d in intraday.index))
print(f"\nUnique dates in intraday (first 10): {unique_dates[:10]}")
print(f"Unique dates in intraday (last 10): {unique_dates[-10:]}")
print(f"Total unique dates: {len(unique_dates)}")

# Does our event date exist?
target = event_date.date()
print(f"\nLooking for date: {target}")
print(f"Is in intraday dates: {target in unique_dates}")

# Try the slice
day_data = intraday[intraday.index.date == target]
print(f"Sliced rows for date: {len(day_data)}")

if len(day_data) > 0:
    session = day_data.between_time('09:30', '16:00')
    print(f"Session bars: {len(session)}")
    if len(session) > 0:
        print(f"Session range: {session.index[0]} to {session.index[-1]}")
