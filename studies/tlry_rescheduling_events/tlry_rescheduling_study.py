"""
TLRY Cannabis Rescheduling Price/Volatility Study

Tests whether U.S. federal cannabis rescheduling headlines create a repeatable edge:
- Large opening gaps
- Strong intraday upside extension (short-squeeze proxy)
- Weak next-day follow-through / mean reversion

Author: Quant Analyst
Date: 2025-12-14
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import requests
import pytz
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

from shared.config.api_clients import AlpacaClient
from shared.config.api_config import APIConfig


class TLRYReschedulingStudy:
    """
    Price/Volatility study for TLRY around U.S. federal cannabis rescheduling events
    """
    
    def __init__(self):
        self.ticker = 'TLRY'
        self.alpaca = AlpacaClient(paper_trading=True)
        self.ct_tz = pytz.timezone('America/Chicago')
        self.utc_tz = pytz.UTC
        
        # News keyword filters (case-insensitive)
        self.keywords = [
            'reschedule', 'rescheduling',
            'schedule iii', 'schedule 3',
            'dea', 'drug enforcement administration',
            'doj', 'department of justice',
            'white house',
            'president',
            'attorney general',
            'cannabis', 'marijuana',
            '280e'
        ]
        
        # Output directory
        self.output_dir = os.path.dirname(__file__)
        self.run_log = []
        
        self.log(f"Initialized TLRY Rescheduling Study at {datetime.now()}")
        self.log(f"Output directory: {self.output_dir}")
        
    def log(self, message: str):
        """Log a message to both console and run log"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        self.run_log.append(log_entry)
        
    def save_run_log(self):
        """Save run log to file"""
        log_path = os.path.join(self.output_dir, 'run_log.txt')
        with open(log_path, 'w') as f:
            f.write('\n'.join(self.run_log))
        self.log(f"Run log saved to {log_path}")
        
    def get_date_range(self) -> Tuple[str, str]:
        """
        Get date range for the study: last 5 years ending at most recent completed trading day
        """
        # Get most recent completed trading day
        try:
            clock = self.alpaca.get_clock()
            is_open = clock.get('is_open', False)
            
            if is_open:
                # Market is open, use previous trading day
                end_date = datetime.now(self.ct_tz) - timedelta(days=1)
            else:
                # Market is closed, use today if it's a weekday, else previous Friday
                end_date = datetime.now(self.ct_tz)
                
            # Ensure we're not on a weekend
            while end_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
                end_date -= timedelta(days=1)
                
            start_date = end_date - timedelta(days=365 * 5)
            
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            
            self.log(f"Date range: {start_str} to {end_str}")
            return start_str, end_str
            
        except Exception as e:
            self.log(f"ERROR getting date range: {e}")
            # Fallback to fixed dates
            end_date = datetime.now() - timedelta(days=1)
            start_date = end_date - timedelta(days=365 * 5)
            return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
    
    def fetch_news(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch news from Alpaca News API with keyword filtering
        
        Returns DataFrame with columns: timestamp, headline, summary, source, symbols
        """
        self.log(f"Fetching news for {self.ticker} from {start_date} to {end_date}")
        
        try:
            # Alpaca News API endpoint
            url = "https://data.alpaca.markets/v1beta1/news"
            headers = {
                'APCA-API-KEY-ID': APIConfig.ALPACA_API_KEY,
                'APCA-API-SECRET-KEY': APIConfig.ALPACA_API_SECRET
            }
            
            all_news = []
            
            # Parse dates
            current_start = datetime.strptime(start_date, '%Y-%m-%d')
            final_end = datetime.strptime(end_date, '%Y-%m-%d')
            
            # Alpaca limits to ~50 items per request, so we'll paginate by month
            while current_start < final_end:
                current_end = min(current_start + timedelta(days=30), final_end)
                
                params = {
                    'symbols': self.ticker,
                    'start': current_start.strftime('%Y-%m-%dT00:00:00Z'),
                    'end': current_end.strftime('%Y-%m-%dT23:59:59Z'),
                    'limit': 50,
                    'sort': 'asc'
                }
                
                self.log(f"  Fetching news batch: {current_start.date()} to {current_end.date()}")
                
                try:
                    response = requests.get(url, headers=headers, params=params)
                    response.raise_for_status()
                    data = response.json()
                    
                    if 'news' in data:
                        all_news.extend(data['news'])
                        self.log(f"    Retrieved {len(data['news'])} articles")
                    
                except Exception as e:
                    self.log(f"    WARNING: Failed to fetch news batch: {e}")
                    
                current_start = current_end + timedelta(days=1)
            
            self.log(f"Total news articles retrieved: {len(all_news)}")
            
            if not all_news:
                self.log("ERROR: No news data retrieved from Alpaca API")
                return pd.DataFrame()
            
            # Convert to DataFrame
            news_df = pd.DataFrame(all_news)
            
            # Parse timestamps
            news_df['timestamp'] = pd.to_datetime(news_df['created_at'])
            news_df['timestamp'] = news_df['timestamp'].dt.tz_convert(self.ct_tz)
            
            # Filter by keywords
            news_df['text_combined'] = (news_df['headline'].fillna('') + ' ' + 
                                       news_df['summary'].fillna('')).str.lower()
            
            def matches_keywords(text: str) -> bool:
                return any(keyword.lower() in text for keyword in self.keywords)
            
            news_df['matches_keywords'] = news_df['text_combined'].apply(matches_keywords)
            filtered_news = news_df[news_df['matches_keywords']].copy()
            
            self.log(f"News articles after keyword filtering: {len(filtered_news)}")
            
            if len(filtered_news) == 0:
                self.log("WARNING: No news articles matched the keyword filters")
                return pd.DataFrame()
            
            # Select relevant columns
            result = filtered_news[[
                'timestamp', 'headline', 'summary', 'source', 'symbols'
            ]].copy()
            
            return result
            
        except Exception as e:
            self.log(f"ERROR fetching news: {e}")
            import traceback
            self.log(traceback.format_exc())
            return pd.DataFrame()
    
    def map_news_to_trading_days(self, news_df: pd.DataFrame, 
                                  trading_days: List[str]) -> pd.DataFrame:
        """
        Map news articles to trading days with pre-open and intraday flags
        
        For trading day T (in CT timezone):
        - Pre-open window: prior trading day 15:00 CT → 08:29 CT
        - Intraday window: 08:30 CT → 15:00 CT
        
        Returns DataFrame with one row per event day
        """
        self.log("Mapping news to trading days...")
        
        if news_df.empty:
            self.log("ERROR: No news to map")
            return pd.DataFrame()
        
        # Convert trading days to datetime
        trading_dates = [pd.Timestamp(d, tz=self.ct_tz) for d in trading_days]
        
        event_days = []
        
        for i, trade_date in enumerate(trading_dates):
            # Define windows
            rth_start = trade_date.replace(hour=8, minute=30, second=0)
            rth_end = trade_date.replace(hour=15, minute=0, second=0)
            
            # Pre-open window: previous close to RTH open
            if i > 0:
                prev_close = trading_dates[i-1].replace(hour=15, minute=0, second=0)
            else:
                prev_close = trade_date.replace(hour=15, minute=0, second=0) - timedelta(days=1)
            
            # Filter news in windows
            pre_open_news = news_df[
                (news_df['timestamp'] > prev_close) & 
                (news_df['timestamp'] < rth_start)
            ]
            
            intraday_news = news_df[
                (news_df['timestamp'] >= rth_start) & 
                (news_df['timestamp'] <= rth_end)
            ]
            
            total_news_count = len(pre_open_news) + len(intraday_news)
            
            if total_news_count > 0:
                # This is an event day
                all_day_news = pd.concat([pre_open_news, intraday_news])
                top_article = all_day_news.iloc[0]  # Use first (earliest) article
                
                event_days.append({
                    'event_date': trade_date.strftime('%Y-%m-%d'),
                    'news_count_total': total_news_count,
                    'news_count_pre_open': len(pre_open_news),
                    'news_count_intraday': len(intraday_news),
                    'pre_open_flag': len(pre_open_news) > 0,
                    'intraday_flag': len(intraday_news) > 0,
                    'top_headline': top_article['headline'],
                    'top_source': top_article.get('source', 'Unknown')
                })
        
        event_df = pd.DataFrame(event_days)
        self.log(f"Identified {len(event_df)} event days")
        
        return event_df
    
    def fetch_daily_bars(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch daily OHLCV bars for TLRY"""
        self.log(f"Fetching daily bars for {self.ticker}")
        
        try:
            # Use Alpaca API directly for better pagination
            url = f"https://data.alpaca.markets/v2/stocks/{self.ticker}/bars"
            headers = {
                'APCA-API-KEY-ID': APIConfig.ALPACA_API_KEY,
                'APCA-API-SECRET-KEY': APIConfig.ALPACA_API_SECRET
            }
            
            params = {
                'timeframe': '1Day',
                'start': start_date + 'T00:00:00Z',
                'end': end_date + 'T23:59:59Z',
                'limit': 10000,
                'feed': 'iex'
            }
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'bars' not in data or not data['bars']:
                self.log("ERROR: No daily bar data returned")
                return pd.DataFrame()
            
            df = pd.DataFrame(data['bars'])
            df['timestamp'] = pd.to_datetime(df['t'])
            df['date'] = df['timestamp'].dt.strftime('%Y-%m-%d')
            
            df = df.rename(columns={
                'o': 'open', 'h': 'high', 'l': 'low', 
                'c': 'close', 'v': 'volume'
            })
            
            df = df[['date', 'open', 'high', 'low', 'close', 'volume']].copy()
            
            self.log(f"Fetched {len(df)} daily bars")
            return df
            
        except Exception as e:
            self.log(f"ERROR fetching daily bars: {e}")
            import traceback
            self.log(traceback.format_exc())
            return pd.DataFrame()
    
    def fetch_intraday_bars(self, date: str, timeframe: str = '1Min') -> pd.DataFrame:
        """
        Fetch intraday bars for a specific date
        Includes premarket (03:00-08:29 CT) and RTH (08:30-15:00 CT)
        """
        try:
            # Convert date to CT timezone start/end
            date_ct = pd.Timestamp(date, tz=self.ct_tz)
            start_time = date_ct.replace(hour=3, minute=0, second=0)
            end_time = date_ct.replace(hour=15, minute=0, second=0)
            
            # Convert to UTC for API
            start_utc = start_time.astimezone(self.utc_tz)
            end_utc = end_time.astimezone(self.utc_tz)
            
            url = f"https://data.alpaca.markets/v2/stocks/{self.ticker}/bars"
            headers = {
                'APCA-API-KEY-ID': APIConfig.ALPACA_API_KEY,
                'APCA-API-SECRET-KEY': APIConfig.ALPACA_API_SECRET
            }
            
            params = {
                'timeframe': timeframe,
                'start': start_utc.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'end': end_utc.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'limit': 10000,
                'feed': 'iex'
            }
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'bars' not in data or not data['bars']:
                return pd.DataFrame()
            
            df = pd.DataFrame(data['bars'])
            df['timestamp'] = pd.to_datetime(df['t']).dt.tz_convert(self.ct_tz)
            
            df = df.rename(columns={
                'o': 'open', 'h': 'high', 'l': 'low', 
                'c': 'close', 'v': 'volume'
            })
            
            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()
            
        except Exception as e:
            self.log(f"  WARNING: Failed to fetch intraday bars for {date}: {e}")
            return pd.DataFrame()
    
    def calculate_event_metrics(self, event_df: pd.DataFrame, 
                                daily_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all price/volatility metrics for each event day
        """
        self.log("Calculating event metrics...")
        
        # Merge with daily data
        daily_df_copy = daily_df.copy()
        daily_df_copy['date'] = daily_df_copy['date'].astype(str)
        event_df['event_date'] = event_df['event_date'].astype(str)
        
        result = event_df.merge(daily_df_copy, left_on='event_date', right_on='date', how='left')
        
        # Calculate metrics for each event
        for idx, row in result.iterrows():
            event_date = row['event_date']
            self.log(f"  Processing event: {event_date}")
            
            # Get previous close
            event_idx = daily_df[daily_df['date'] == event_date].index
            if len(event_idx) == 0 or event_idx[0] == 0:
                result.at[idx, 'prev_close'] = np.nan
                continue
            
            prev_idx = event_idx[0] - 1
            prev_close = daily_df.iloc[prev_idx]['close']
            result.at[idx, 'prev_close'] = prev_close
            
            # Fetch intraday bars for this date
            intraday_df = self.fetch_intraday_bars(event_date, timeframe='1Min')
            
            if intraday_df.empty:
                # Try 5-minute bars if 1-minute not available
                self.log(f"    No 1-min data, trying 5-min bars")
                intraday_df = self.fetch_intraday_bars(event_date, timeframe='5Min')
            
            if not intraday_df.empty:
                # Get RTH open (08:30 CT)
                rth_bars = intraday_df[intraday_df['timestamp'].dt.hour >= 8]
                rth_bars = rth_bars[
                    (rth_bars['timestamp'].dt.hour > 8) | 
                    (rth_bars['timestamp'].dt.minute >= 30)
                ]
                
                if not rth_bars.empty:
                    open_price = rth_bars.iloc[0]['open']
                    result.at[idx, 'open_price'] = open_price
                    
                    # RTH high and close
                    rth_close_bars = rth_bars[rth_bars['timestamp'].dt.hour < 15]
                    if not rth_close_bars.empty:
                        day_high_rth = rth_close_bars['high'].max()
                        result.at[idx, 'day_high_rth'] = day_high_rth
                        result.at[idx, 'open_to_high_pct_rth'] = ((day_high_rth - open_price) / open_price) * 100
                        
                        # Time to high
                        high_bar = rth_close_bars[rth_close_bars['high'] == day_high_rth].iloc[0]
                        high_time = high_bar['timestamp']
                        rth_open_time = rth_bars.iloc[0]['timestamp']
                        time_to_high_minutes = (high_time - rth_open_time).total_seconds() / 60
                        result.at[idx, 'time_to_high_minutes'] = time_to_high_minutes
                        
                        # First hour high
                        first_hour_cutoff = rth_open_time + timedelta(hours=1)
                        first_hour_bars = rth_bars[rth_bars['timestamp'] <= first_hour_cutoff]
                        if not first_hour_bars.empty:
                            first_hour_high = first_hour_bars['high'].max()
                            result.at[idx, 'firsthour_open_to_high_pct'] = ((first_hour_high - open_price) / open_price) * 100
                else:
                    result.at[idx, 'open_price'] = row['open']  # Fallback to daily open
            else:
                result.at[idx, 'open_price'] = row['open']  # Fallback to daily open
            
            # Calculate gap and close metrics
            if not pd.isna(result.at[idx, 'prev_close']) and not pd.isna(result.at[idx, 'open_price']):
                result.at[idx, 'open_gap_pct'] = ((result.at[idx, 'open_price'] - result.at[idx, 'prev_close']) / 
                                                   result.at[idx, 'prev_close']) * 100
            
            if not pd.isna(result.at[idx, 'open_price']):
                result.at[idx, 'open_to_close_pct'] = ((row['close'] - result.at[idx, 'open_price']) / 
                                                        result.at[idx, 'open_price']) * 100
            
            # T+1 return
            if len(event_idx) > 0 and event_idx[0] < len(daily_df) - 1:
                next_idx = event_idx[0] + 1
                next_close = daily_df.iloc[next_idx]['close']
                result.at[idx, 'tplus1_return_pct'] = ((next_close - row['close']) / row['close']) * 100
            
            # T+3 return
            if len(event_idx) > 0 and event_idx[0] < len(daily_df) - 3:
                next3_idx = event_idx[0] + 3
                next3_close = daily_df.iloc[next3_idx]['close']
                result.at[idx, 'tplus3_return_pct'] = ((next3_close - row['close']) / row['close']) * 100
            
            # Volume metrics
            result.at[idx, 'event_volume'] = row['volume']
            
            # 6-month average volume
            if len(event_idx) > 0 and event_idx[0] >= 126:
                lookback_start = max(0, event_idx[0] - 126)
                lookback_end = event_idx[0]
                avg_vol = daily_df.iloc[lookback_start:lookback_end]['volume'].mean()
                result.at[idx, 'avg_volume_6mo'] = avg_vol
                result.at[idx, 'volume_spike_ratio'] = row['volume'] / avg_vol if avg_vol > 0 else np.nan
        
        # Select final columns
        final_cols = [
            'event_date', 'news_count_total', 'news_count_pre_open', 'news_count_intraday',
            'pre_open_flag', 'intraday_flag', 'top_headline', 'top_source',
            'prev_close', 'open_price', 'open_gap_pct', 'day_high_rth', 'open_to_high_pct_rth',
            'close', 'open_to_close_pct', 'tplus1_return_pct', 'tplus3_return_pct',
            'event_volume', 'avg_volume_6mo', 'volume_spike_ratio',
            'time_to_high_minutes', 'firsthour_open_to_high_pct'
        ]
        
        # Rename close column
        result = result.rename(columns={'close': 'close_price'})
        final_cols = [c if c != 'close' else 'close_price' for c in final_cols]
        
        result = result[final_cols].copy()
        
        self.log(f"Calculated metrics for {len(result)} events")
        return result
    
    def calculate_summary_stats(self, master_df: pd.DataFrame) -> Dict:
        """Calculate summary statistics"""
        self.log("Calculating summary statistics...")
        
        stats_dict = {
            'n_events': len(master_df),
            'date_range': {
                'start': master_df['event_date'].min(),
                'end': master_df['event_date'].max()
            }
        }
        
        # Metrics to summarize
        metrics = ['open_gap_pct', 'open_to_high_pct_rth', 'open_to_close_pct', 'tplus1_return_pct', 'tplus3_return_pct']
        
        for metric in metrics:
            if metric in master_df.columns:
                data = master_df[metric].dropna()
                if len(data) > 0:
                    stats_dict[metric] = {
                        'mean': float(data.mean()),
                        'median': float(data.median()),
                        'std': float(data.std()),
                        'min': float(data.min()),
                        'max': float(data.max()),
                        'q10': float(data.quantile(0.10)),
                        'q25': float(data.quantile(0.25)),
                        'q75': float(data.quantile(0.75)),
                        'q90': float(data.quantile(0.90))
                    }
        
        # Percentage with negative T+1 returns
        tplus1_data = master_df['tplus1_return_pct'].dropna()
        if len(tplus1_data) > 0:
            pct_negative = (tplus1_data < 0).sum() / len(tplus1_data) * 100
            stats_dict['pct_negative_tplus1'] = float(pct_negative)
        
        # Percentage with negative T+3 returns
        tplus3_data = master_df['tplus3_return_pct'].dropna()
        if len(tplus3_data) > 0:
            pct_negative_t3 = (tplus3_data < 0).sum() / len(tplus3_data) * 100
            stats_dict['pct_negative_tplus3'] = float(pct_negative_t3)
        
        # Correlations
        if 'open_gap_pct' in master_df.columns and 'open_to_high_pct_rth' in master_df.columns:
            corr_data = master_df[['open_gap_pct', 'open_to_high_pct_rth']].dropna()
            if len(corr_data) > 2:
                corr = corr_data['open_gap_pct'].corr(corr_data['open_to_high_pct_rth'])
                stats_dict['correlation_gap_vs_extension'] = float(corr)
        
        if 'volume_spike_ratio' in master_df.columns and 'open_to_high_pct_rth' in master_df.columns:
            corr_data = master_df[['volume_spike_ratio', 'open_to_high_pct_rth']].dropna()
            if len(corr_data) > 2:
                corr = corr_data['volume_spike_ratio'].corr(corr_data['open_to_high_pct_rth'])
                stats_dict['correlation_volume_vs_extension'] = float(corr)
        
        return stats_dict
    
    def create_plots(self, master_df: pd.DataFrame):
        """Create required plots"""
        self.log("Creating plots...")
        
        sns.set_style("whitegrid")
        
        # 1. Histogram: open_to_high_pct_rth
        if 'open_to_high_pct_rth' in master_df.columns:
            data = master_df['open_to_high_pct_rth'].dropna()
            if len(data) > 0:
                plt.figure(figsize=(10, 6))
                plt.hist(data, bins=20, edgecolor='black', alpha=0.7)
                plt.axvline(data.mean(), color='red', linestyle='--', linewidth=2, label=f'Mean: {data.mean():.2f}%')
                plt.axvline(data.median(), color='green', linestyle='--', linewidth=2, label=f'Median: {data.median():.2f}%')
                plt.xlabel('Open-to-High Extension (%)', fontsize=12)
                plt.ylabel('Frequency', fontsize=12)
                plt.title('TLRY: Intraday Upside Extension on Event Days', fontsize=14, fontweight='bold')
                plt.legend()
                plt.grid(alpha=0.3)
                plt.tight_layout()
                plt.savefig(os.path.join(self.output_dir, 'tlry_open_to_high_hist.png'), dpi=150)
                plt.close()
                self.log("  Saved: tlry_open_to_high_hist.png")
        
        # 2. Scatter: open_gap_pct vs open_to_high_pct_rth
        if 'open_gap_pct' in master_df.columns and 'open_to_high_pct_rth' in master_df.columns:
            scatter_data = master_df[['open_gap_pct', 'open_to_high_pct_rth']].dropna()
            if len(scatter_data) > 2:
                plt.figure(figsize=(10, 6))
                x = scatter_data['open_gap_pct']
                y = scatter_data['open_to_high_pct_rth']
                plt.scatter(x, y, alpha=0.6, s=80)
                
                # Linear fit
                z = np.polyfit(x, y, 1)
                p = np.poly1d(z)
                plt.plot(x, p(x), "r--", alpha=0.8, linewidth=2, label=f'Fit: y={z[0]:.2f}x+{z[1]:.2f}')
                
                # Correlation
                corr = x.corr(y)
                plt.text(0.05, 0.95, f'Correlation: {corr:.3f}', 
                        transform=plt.gca().transAxes, fontsize=12, verticalalignment='top',
                        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
                
                plt.xlabel('Opening Gap (%)', fontsize=12)
                plt.ylabel('Open-to-High Extension (%)', fontsize=12)
                plt.title('TLRY: Gap vs Intraday Extension', fontsize=14, fontweight='bold')
                plt.legend()
                plt.grid(alpha=0.3)
                plt.tight_layout()
                plt.savefig(os.path.join(self.output_dir, 'tlry_gap_vs_extension_scatter.png'), dpi=150)
                plt.close()
                self.log("  Saved: tlry_gap_vs_extension_scatter.png")
        
        # 3. Timeline: event_date vs open_to_high_pct_rth
        if 'event_date' in master_df.columns and 'open_to_high_pct_rth' in master_df.columns:
            timeline_data = master_df[['event_date', 'open_to_high_pct_rth']].dropna()
            if len(timeline_data) > 0:
                timeline_data['event_date'] = pd.to_datetime(timeline_data['event_date'])
                timeline_data = timeline_data.sort_values('event_date')
                
                plt.figure(figsize=(14, 6))
                plt.plot(timeline_data['event_date'], timeline_data['open_to_high_pct_rth'], 
                        marker='o', linestyle='-', linewidth=1.5, markersize=6)
                plt.axhline(0, color='black', linestyle='--', alpha=0.5)
                plt.xlabel('Event Date', fontsize=12)
                plt.ylabel('Open-to-High Extension (%)', fontsize=12)
                plt.title('TLRY: Intraday Extension Timeline', fontsize=14, fontweight='bold')
                plt.grid(alpha=0.3)
                plt.xticks(rotation=45)
                plt.tight_layout()
                plt.savefig(os.path.join(self.output_dir, 'tlry_event_timeline.png'), dpi=150)
                plt.close()
                self.log("  Saved: tlry_event_timeline.png")
    
    def run(self):
        """Execute the full study"""
        self.log("="*60)
        self.log("STARTING TLRY RESCHEDULING STUDY")
        self.log("="*60)
        
        try:
            # 1. Get date range
            start_date, end_date = self.get_date_range()
            
            # 2. Fetch daily bars first (to get trading days)
            daily_df = self.fetch_daily_bars(start_date, end_date)
            
            if daily_df.empty:
                self.log("CRITICAL ERROR: Failed to fetch daily price data. Study cannot proceed.")
                self.save_run_log()
                return
            
            trading_days = daily_df['date'].tolist()
            self.log(f"Total trading days in range: {len(trading_days)}")
            
            # 3. Fetch news
            news_df = self.fetch_news(start_date, end_date)
            
            if news_df.empty:
                self.log("CRITICAL ERROR: No news data available. Study cannot proceed.")
                self.save_run_log()
                return
            
            # 4. Map news to trading days
            event_df = self.map_news_to_trading_days(news_df, trading_days)
            
            if event_df.empty:
                self.log("CRITICAL ERROR: No event days identified. Study cannot proceed.")
                self.save_run_log()
                return
            
            # 5. Calculate metrics
            master_df = self.calculate_event_metrics(event_df, daily_df)
            
            # 6. Save master table
            master_path = os.path.join(self.output_dir, 'tlry_rescheduling_event_master_table.csv')
            master_df.to_csv(master_path, index=False)
            self.log(f"Saved master table: {master_path}")
            
            # 7. Calculate summary stats
            summary_stats = self.calculate_summary_stats(master_df)
            
            # 8. Save summary
            summary_path = os.path.join(self.output_dir, 'tlry_rescheduling_event_summary.json')
            with open(summary_path, 'w') as f:
                json.dump(summary_stats, f, indent=2)
            self.log(f"Saved summary stats: {summary_path}")
            
            # 9. Create plots
            self.create_plots(master_df)
            
            # 10. Save run log
            self.save_run_log()
            
            # 11. Print final summary to console
            self.log("="*60)
            self.log("STUDY COMPLETE - FINAL SUMMARY")
            self.log("="*60)
            print(f"\nNumber of event days: {summary_stats['n_events']}")
            
            if 'open_gap_pct' in summary_stats:
                print(f"\nOpening Gap:")
                print(f"  Mean: {summary_stats['open_gap_pct']['mean']:.2f}%")
                print(f"  Median: {summary_stats['open_gap_pct']['median']:.2f}%")
            
            if 'open_to_high_pct_rth' in summary_stats:
                print(f"\nOpen-to-High Extension (RTH):")
                print(f"  Mean: {summary_stats['open_to_high_pct_rth']['mean']:.2f}%")
                print(f"  Median: {summary_stats['open_to_high_pct_rth']['median']:.2f}%")
            
            if 'tplus1_return_pct' in summary_stats:
                print(f"\nNext-Day (T+1) Return:")
                print(f"  Mean: {summary_stats['tplus1_return_pct']['mean']:.2f}%")
                print(f"  Median: {summary_stats['tplus1_return_pct']['median']:.2f}%")
            
            if 'pct_negative_tplus1' in summary_stats:
                print(f"  % Negative T+1 Returns: {summary_stats['pct_negative_tplus1']:.1f}%")
            
            if 'tplus3_return_pct' in summary_stats:
                print(f"\nThird-Day (T+3) Return:")
                print(f"  Mean: {summary_stats['tplus3_return_pct']['mean']:.2f}%")
                print(f"  Median: {summary_stats['tplus3_return_pct']['median']:.2f}%")
            
            if 'pct_negative_tplus3' in summary_stats:
                print(f"  % Negative T+3 Returns: {summary_stats['pct_negative_tplus3']:.1f}%")
            
            # Interpretation
            print("\n" + "="*60)
            print("INTERPRETATION")
            print("="*60)
            
            gap_mean = summary_stats.get('open_gap_pct', {}).get('mean', 0)
            extension_mean = summary_stats.get('open_to_high_pct_rth', {}).get('mean', 0)
            tplus1_mean = summary_stats.get('tplus1_return_pct', {}).get('mean', 0)
            pct_negative = summary_stats.get('pct_negative_tplus1', 0)
            
            print(f"\nBehavior Pattern:")
            if gap_mean > 2 and extension_mean > 3 and pct_negative > 50:
                print("✓ MATCHES 'Gap + Squeeze + Next-Day Fade' hypothesis")
                print(f"  - Large positive opening gaps (avg {gap_mean:.1f}%)")
                print(f"  - Strong intraday extension (avg {extension_mean:.1f}%)")
                print(f"  - Weak follow-through: {pct_negative:.0f}% fade next day")
            elif gap_mean > 2 and extension_mean > 3:
                print("⚠ PARTIAL MATCH: Gap + Squeeze, but limited next-day fade")
                print(f"  - Opening gaps and intraday strength present")
                print(f"  - But only {pct_negative:.0f}% fade next day (expected >50%)")
            else:
                print("✗ DOES NOT match hypothesis")
                print(f"  - Insufficient gap/extension pattern")
            
            print("\n" + "="*60)
            
        except Exception as e:
            self.log(f"CRITICAL ERROR during study execution: {e}")
            import traceback
            self.log(traceback.format_exc())
            self.save_run_log()
            raise


if __name__ == '__main__':
    study = TLRYReschedulingStudy()
    study.run()
