"""
Analyze Alibaba (BABA) stock performance on China NBS conference dates
Tracks gaps, continuation, and multi-day performance
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time
from config.api_clients import TiingoClient, FMPClient
from config.api_config import APIConfig


def get_trading_dates_around(target_date: str, days_before: int = 5, days_after: int = 5) -> List[str]:
    """Get trading dates around target date"""
    date_obj = datetime.strptime(target_date, "%Y-%m-%d")
    dates = []
    
    # Get range of dates (accounting for weekends/holidays)
    start_date = date_obj - timedelta(days=days_before)
    end_date = date_obj + timedelta(days=days_after)
    
    current = start_date
    while current <= end_date:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    
    return dates


def analyze_baba_on_nbs_dates(nbs_dates: List[str]) -> List[Dict]:
    """
    Analyze BABA price action on NBS conference dates
    
    Returns:
        List of analysis results for each date
    """
    results = []
    
    # Try Tiingo first (usually has good historical data)
    try:
        print("Initializing API client...")
        client = TiingoClient()
        
        for i, nbs_date in enumerate(nbs_dates, 1):
            print(f"\nAnalyzing {i}/{len(nbs_dates)}: {nbs_date}")
            
            try:
                # Get price data around the NBS date
                date_obj = datetime.strptime(nbs_date, "%Y-%m-%d")
                start_date = (date_obj - timedelta(days=10)).strftime("%Y-%m-%d")
                end_date = (date_obj + timedelta(days=10)).strftime("%Y-%m-%d")
                
                # Fetch BABA data
                data = client.get_daily_prices('BABA', start_date=start_date, end_date=end_date)
                
                if not data or len(data) == 0:
                    print(f"  ⚠ No data available for {nbs_date}")
                    results.append({
                        'date': nbs_date,
                        'error': 'No data available'
                    })
                    continue
                
                # Convert to dict by date for easier lookup
                price_data = {item['date'][:10]: item for item in data}
                
                # Find the NBS date in the data
                if nbs_date not in price_data:
                    # Try to find the next trading day
                    next_days = [(date_obj + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(5)]
                    actual_date = None
                    for day in next_days:
                        if day in price_data:
                            actual_date = day
                            break
                    
                    if not actual_date:
                        print(f"  ⚠ {nbs_date} not a trading day")
                        results.append({
                            'date': nbs_date,
                            'error': 'Not a trading day'
                        })
                        continue
                else:
                    actual_date = nbs_date
                
                # Get previous trading day
                prev_date = None
                for i in range(1, 10):
                    check_date = (datetime.strptime(actual_date, "%Y-%m-%d") - timedelta(days=i)).strftime("%Y-%m-%d")
                    if check_date in price_data:
                        prev_date = check_date
                        break
                
                if not prev_date:
                    print(f"  ⚠ Could not find previous trading day")
                    continue
                
                # Get days after
                day_plus_2 = None
                day_plus_3 = None
                trading_days_after = []
                for i in range(1, 15):
                    check_date = (datetime.strptime(actual_date, "%Y-%m-%d") + timedelta(days=i)).strftime("%Y-%m-%d")
                    if check_date in price_data:
                        trading_days_after.append(check_date)
                
                if len(trading_days_after) >= 2:
                    day_plus_2 = trading_days_after[1]
                if len(trading_days_after) >= 3:
                    day_plus_3 = trading_days_after[2]
                
                # Extract price data
                prev_close = price_data[prev_date]['close']
                day_open = price_data[actual_date]['open']
                day_high = price_data[actual_date]['high']
                day_low = price_data[actual_date]['low']
                day_close = price_data[actual_date]['close']
                
                # Calculate metrics
                gap_pct = ((day_open - prev_close) / prev_close) * 100
                gap_direction = "UP" if gap_pct > 0.5 else "DOWN" if gap_pct < -0.5 else "FLAT"
                
                intraday_pct = ((day_close - day_open) / day_open) * 100
                continuation = None
                if abs(gap_pct) > 0.5:
                    if (gap_pct > 0 and intraday_pct > 0) or (gap_pct < 0 and intraday_pct < 0):
                        continuation = "YES"
                    elif (gap_pct > 0 and intraday_pct < -0.5) or (gap_pct < 0 and intraday_pct > 0.5):
                        continuation = "REVERSAL"
                    else:
                        continuation = "FLAT"
                
                # Performance 2-3 days out
                perf_2d = None
                perf_3d = None
                if day_plus_2:
                    close_2d = price_data[day_plus_2]['close']
                    perf_2d = ((close_2d - day_close) / day_close) * 100
                
                if day_plus_3:
                    close_3d = price_data[day_plus_3]['close']
                    perf_3d = ((close_3d - day_close) / day_close) * 100
                
                result = {
                    'nbs_date': nbs_date,
                    'trading_date': actual_date,
                    'prev_close': round(prev_close, 2),
                    'open': round(day_open, 2),
                    'high': round(day_high, 2),
                    'low': round(day_low, 2),
                    'close': round(day_close, 2),
                    'gap_pct': round(gap_pct, 2),
                    'gap_direction': gap_direction,
                    'intraday_pct': round(intraday_pct, 2),
                    'continuation': continuation,
                    'perf_2d': round(perf_2d, 2) if perf_2d is not None else None,
                    'perf_3d': round(perf_3d, 2) if perf_3d is not None else None,
                    'day_plus_2_date': day_plus_2,
                    'day_plus_3_date': day_plus_3
                }
                
                results.append(result)
                
                # Print summary
                print(f"  📊 Gap: {gap_direction} {gap_pct:+.2f}%")
                print(f"  📈 Intraday: {intraday_pct:+.2f}% | Continuation: {continuation}")
                print(f"  🎯 2-Day: {perf_2d:+.2f}% | 3-Day: {perf_3d:+.2f}%" if perf_2d and perf_3d else "  🎯 Forward data limited")
                
                # Rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                print(f"  ❌ Error analyzing {nbs_date}: {str(e)}")
                results.append({
                    'date': nbs_date,
                    'error': str(e)
                })
        
    except Exception as e:
        print(f"❌ API Error: {str(e)}")
        print("\nTrying alternative API (FMP)...")
        
        # Try FMP as backup
        try:
            client = FMPClient()
            print("Note: FMP may have limited historical intraday data")
        except Exception as e2:
            print(f"❌ Could not initialize alternative API: {str(e2)}")
            return []
    
    return results


def format_results(results: List[Dict]) -> str:
    """Format results into a readable report"""
    report = []
    report.append("\n" + "="*100)
    report.append("ALIBABA (BABA) PERFORMANCE ON CHINA NBS CONFERENCE DATES")
    report.append("="*100 + "\n")
    
    # Statistics
    valid_results = [r for r in results if 'error' not in r]
    
    if valid_results:
        gaps_up = [r for r in valid_results if r['gap_direction'] == 'UP']
        gaps_down = [r for r in valid_results if r['gap_direction'] == 'DOWN']
        continuations = [r for r in valid_results if r.get('continuation') == 'YES']
        reversals = [r for r in valid_results if r.get('continuation') == 'REVERSAL']
        
        avg_gap = sum(r['gap_pct'] for r in valid_results) / len(valid_results)
        avg_intraday = sum(r['intraday_pct'] for r in valid_results) / len(valid_results)
        
        perf_2d_data = [r['perf_2d'] for r in valid_results if r.get('perf_2d') is not None]
        perf_3d_data = [r['perf_3d'] for r in valid_results if r.get('perf_3d') is not None]
        
        avg_2d = sum(perf_2d_data) / len(perf_2d_data) if perf_2d_data else 0
        avg_3d = sum(perf_3d_data) / len(perf_3d_data) if perf_3d_data else 0
        
        report.append("SUMMARY STATISTICS:")
        report.append(f"  Total NBS Dates Analyzed: {len(valid_results)}")
        report.append(f"  Gaps Up: {len(gaps_up)} ({len(gaps_up)/len(valid_results)*100:.1f}%)")
        report.append(f"  Gaps Down: {len(gaps_down)} ({len(gaps_down)/len(valid_results)*100:.1f}%)")
        report.append(f"  Continuation Rate: {len(continuations)}/{len(valid_results)} ({len(continuations)/len(valid_results)*100:.1f}%)")
        report.append(f"  Reversal Rate: {len(reversals)}/{len(valid_results)} ({len(reversals)/len(valid_results)*100:.1f}%)")
        report.append(f"  Average Gap: {avg_gap:+.2f}%")
        report.append(f"  Average Intraday Move: {avg_intraday:+.2f}%")
        report.append(f"  Average 2-Day Performance: {avg_2d:+.2f}%")
        report.append(f"  Average 3-Day Performance: {avg_3d:+.2f}%")
        report.append("\n" + "-"*100 + "\n")
    
    # Detailed results
    report.append("DETAILED RESULTS:\n")
    
    for i, result in enumerate(results, 1):
        if 'error' in result:
            report.append(f"{i}. {result['date']}: ❌ {result['error']}")
            continue
        
        report.append(f"{i}. NBS Date: {result['nbs_date']} (Trading: {result['trading_date']})")
        report.append(f"   Previous Close: ${result['prev_close']}")
        report.append(f"   Opening Gap: {result['gap_direction']} {result['gap_pct']:+.2f}%")
        report.append(f"   Day Range: ${result['low']} - ${result['high']}")
        report.append(f"   Close: ${result['close']} ({result['intraday_pct']:+.2f}% intraday)")
        report.append(f"   Continuation: {result['continuation']}")
        
        if result['perf_2d'] is not None:
            report.append(f"   2-Day Performance: {result['perf_2d']:+.2f}% (close: {result['day_plus_2_date']})")
        if result['perf_3d'] is not None:
            report.append(f"   3-Day Performance: {result['perf_3d']:+.2f}% (close: {result['day_plus_3_date']})")
        
        report.append("")
    
    return "\n".join(report)


def main():
    """Main execution"""
    # NBS conference dates (from previous script)
    nbs_dates = [
        "2024-11-15", "2024-10-18", "2024-09-14", "2024-08-15",
        "2024-07-15", "2024-06-17", "2024-05-17", "2024-04-16",
        "2024-03-18", "2024-02-29", "2024-01-17",
        "2023-12-15", "2023-11-15", "2023-10-18", "2023-09-15",
        "2023-08-15", "2023-07-17", "2023-06-15", "2023-05-16",
        "2023-04-18"
    ]
    
    print("Starting BABA analysis on NBS conference dates...")
    print(f"Total dates to analyze: {len(nbs_dates)}")
    
    results = analyze_baba_on_nbs_dates(nbs_dates)
    
    # Format and display results
    report = format_results(results)
    print(report)
    
    # Save to file
    output_file = "baba_nbs_analysis.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✓ Full analysis saved to {output_file}")
    
    # Also save CSV for Excel analysis
    csv_file = "baba_nbs_analysis.csv"
    with open(csv_file, 'w', encoding='utf-8') as f:
        f.write("NBS_Date,Trading_Date,Prev_Close,Open,High,Low,Close,Gap_%,Gap_Direction,Intraday_%,Continuation,2Day_%,3Day_%\n")
        for r in results:
            if 'error' not in r:
                f.write(f"{r['nbs_date']},{r['trading_date']},{r['prev_close']},{r['open']},{r['high']},{r['low']},{r['close']},")
                f.write(f"{r['gap_pct']},{r['gap_direction']},{r['intraday_pct']},{r['continuation']},")
                f.write(f"{r.get('perf_2d', '')},{r.get('perf_3d', '')}\n")
    
    print(f"✓ CSV data saved to {csv_file}")
    
    return results


if __name__ == "__main__":
    results = main()
