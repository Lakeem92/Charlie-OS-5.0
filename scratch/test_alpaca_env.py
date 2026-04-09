"""
Minimal Alpaca Fetch Test
Test that environment loading and Alpaca API work correctly.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import data_router which should trigger env loading via api_config
from shared.data_router import DataRouter

def test_alpaca_fetch():
    """Test minimal 5-bar TSLA fetch from Alpaca."""
    try:
        print("Testing Alpaca connection...")
        
        # Fetch just 5 bars to test connection
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=10)  # Get last ~5 trading days
        
        df = DataRouter.get_price_data(
            ticker='TSLA',
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            timeframe='daily',
            source='yfinance',  # Use yfinance as primary for daily
            fallback=False
        )
        
        if df is not None and len(df) > 0:
            print(f"✓ Fetched {len(df)} bars")
            print(f"  Date range: {df.index[0]} to {df.index[-1]}")
            print("\nALPACA OK")
            return True
        else:
            print("✗ No data returned")
            print("\nALPACA NOT OK")
            return False
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        print("\nALPACA NOT OK")
        return False


if __name__ == "__main__":
    test_alpaca_fetch()
