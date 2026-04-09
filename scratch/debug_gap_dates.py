import sys
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
from shared.data_router import DataRouter
import pandas as pd

# Pull a known ticker with 5min data
df = DataRouter.get_price_data('TSLA', '2024-06-01', end_date='2024-06-05', timeframe='5min')
print(f'Index type: {type(df.index)}')
print(f'Index dtype: {df.index.dtype}')
print(f'First 3 index values: {df.index[:3].tolist()}')
tz = getattr(df.index, 'tz', 'none')
print(f'Index tz: {tz}')
print(f'First .date: {df.index[0].date()}')
print(f'Type of .date: {type(df.index[0].date())}')

# Now check daily
dd = DataRouter.get_price_data('TSLA', '2024-06-01', end_date='2024-06-05', timeframe='daily')
print(f'Daily index dtype: {dd.index.dtype}')
print(f'Daily first 3: {dd.index[:3].tolist()}')
ts = pd.Timestamp(dd.index[0])
print(f'Timestamp from daily: {ts}, .date(): {ts.date()}, type: {type(ts.date())}')

# Test date matching
event_date = pd.Timestamp(dd.index[0])
dates_in_intraday = set(d.date() for d in df.index)
print(f'Unique dates in intraday: {dates_in_intraday}')
print(f'event_date.date(): {event_date.date()}')
print(f'Match: {event_date.date() in dates_in_intraday}')

# Test between_time
day_data = df[df.index.date == event_date.date()]
print(f'Day slice length: {len(day_data)}')
if len(day_data) > 0:
    session = day_data.between_time('09:30', '16:00')
    print(f'Session length: {len(session)}')
