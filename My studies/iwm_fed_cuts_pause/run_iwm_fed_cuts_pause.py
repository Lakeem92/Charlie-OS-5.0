import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# Define the Fed cut then pause events
events = [
    {
        'cut_date': '2024-09-19',
        'pause_end': '2024-12-19',
        'description': 'Fed cuts 50bps on Sep 19, 2024, then pauses at Nov and Dec meetings'
    },
    {
        'cut_date': '2022-11-03',
        'pause_end': '2022-12-15',
        'description': 'Fed cuts 75bps on Nov 3, 2022, then pauses at Dec meeting'
    }
]

def analyze_iwm_event(cut_date_str, pause_end_str, description):
    cut_date = datetime.strptime(cut_date_str, '%Y-%m-%d').date()
    pause_end = datetime.strptime(pause_end_str, '%Y-%m-%d').date()
    
    # Get data from 30 days before cut to 30 days after pause end
    start_date = cut_date - timedelta(days=30)
    end_date = pause_end + timedelta(days=30)
    
    # Download IWM data
    iwm = yf.download('IWM', start=start_date, end=end_date)
    
    if iwm.empty:
        print(f"No data for {description}")
        return
    
    print(f"Data shape: {iwm.shape}")
    print(f"Index type: {type(iwm.index)}")
    print(f"Sample index: {iwm.index[:5]}")
    print(f"Cut date str: {cut_date_str}")
    print(f"Has cut date: {cut_date_str in iwm.index}")
    
    # Calculate returns
    iwm['Daily Return'] = iwm[('Close', 'IWM')].pct_change()
    
    # Periods
    pre_cut = iwm.loc[:cut_date_str]
    cut_to_pause = iwm.loc[cut_date_str:pause_end_str]
    post_pause = iwm.loc[pause_end_str:]
    
    # Stats
    stats = {}
    for period_name, period_data in [('Pre-Cut', pre_cut), ('Cut to Pause', cut_to_pause), ('Post-Pause', post_pause)]:
        if not period_data.empty:
            cum_return = (period_data[('Close', 'IWM')].iloc[-1] / period_data[('Close', 'IWM')].iloc[0] - 1) * 100
            volatility = period_data['Daily Return'].std() * (252 ** 0.5) * 100  # Annualized vol
            max_drawdown = ((period_data[('Close', 'IWM')] / period_data[('Close', 'IWM')].cummax()) - 1).min() * 100
            stats[period_name] = {
                'Cumulative Return (%)': cum_return,
                'Annualized Volatility (%)': volatility,
                'Max Drawdown (%)': max_drawdown
            }
    
    print(f"\n{description}")
    print(f"Data period: {start_date} to {end_date}")
    
    # Get prices, handle if date not in data
    try:
        cut_price = iwm.loc[cut_date_str, ('Close', 'IWM')]
        print(f"IWM price on cut date: ${cut_price:.2f}")
    except KeyError:
        print(f"Cut date {cut_date_str} not in data (weekend/holiday)")
        cut_price = None
    
    try:
        pause_price = iwm.loc[pause_end_str, ('Close', 'IWM')]
        print(f"IWM price on pause end: ${pause_price:.2f}")
    except KeyError:
        print(f"Pause end {pause_end_str} not in data (weekend/holiday)")
        pause_price = None
    
    for period, stat in stats.items():
        print(f"{period}: Return {stat['Cumulative Return (%)']:.2f}%, Vol {stat['Annualized Volatility (%)']:.2f}%, Max DD {stat['Max Drawdown (%)']:.2f}%")
    
    # Plot
    plt.figure(figsize=(12, 6))
    plt.plot(iwm.index, iwm[('Close', 'IWM')], label='IWM Close')
    plt.axvline(pd.to_datetime(cut_date_str), color='red', linestyle='--', label='Cut Date')
    plt.axvline(pd.to_datetime(pause_end_str), color='blue', linestyle='--', label='Pause End')
    plt.title(f'IWM Price Around {description}')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend()
    plt.grid(True)
    plt.show()

def main():
    for event in events:
        analyze_iwm_event(event['cut_date'], event['pause_end'], event['description'])

if __name__ == "__main__":
    main()