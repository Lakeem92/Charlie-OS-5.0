import sys
import pandas as pd
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')
from tools.prediction_markets.pm_data_loader import (
    search_markets, get_market_probability
)

# Test 1: Recession search
print("=== RECESSION SEARCH ===")
try:
    rec = search_markets("recession", source="polymarket")
    if not rec.empty:
        for _, row in rec.head(3).iterrows():
            print(f"  {row.get('market_id','?')} | "
                  f"{str(row.get('question','?'))[:60]} | "
                  f"P={row.get('outcome_prices','?')}")
    else:
        print("  No results")
except Exception as e:
    print(f"  Error: {e}")

# Test 2: Fed cut probability time series
print("\n=== FED CUT PROBABILITY TIME SERIES ===")
print("Market 616902 (No cuts in 2026):")
try:
    series = get_market_probability("616902", days=90)
    if not series.empty:
        print(f"  {len(series)} daily readings")
        print(f"  Date range: {series.index[0].date()} "
              f"to {series.index[-1].date()}")
        print(f"  Current (last): {series.iloc[-1]:.1f}%")
        if len(series) >= 30:
            print(f"  30d ago: {series.iloc[-30]:.1f}%")
        else:
            print(f"  (fewer than 30 readings available)")
        if len(series) >= 8:
            roc_7d = series.iloc[-1] - series.iloc[-8]
            print(f"  7d ROC: {roc_7d:+.1f}%")
    else:
        print("  Empty series -- check token mapping")
except Exception as e:
    print(f"  Error: {e}")

# Test 3: Recession probability time series
print("\n=== RECESSION PROBABILITY TIME SERIES ===")
try:
    rec = search_markets("recession", source="polymarket")
    if not rec.empty:
        rec_id = str(rec.iloc[0].get('market_id', rec.iloc[0].get('id', '')))
        print(f"Using market: {rec_id} | {str(rec.iloc[0].get('question',''))[:60]}")
        rec_series = get_market_probability(rec_id, days=90)
        if not rec_series.empty:
            print(f"  {len(rec_series)} daily readings")
            print(f"  Date range: {rec_series.index[0].date()} to {rec_series.index[-1].date()}")
            print(f"  Current (last): {rec_series.iloc[-1]:.1f}%")
            if len(rec_series) >= 8:
                roc = rec_series.iloc[-1] - rec_series.iloc[-8]
                print(f"  7d ROC: {roc:+.1f}%")
        else:
            print("  Empty -- check token mapping")
    else:
        print("  No recession markets found")
except Exception as e:
    print(f"  Error: {e}")

# Test 4: Inflation unicode test
print("\n=== INFLATION SEARCH (ENCODING TEST) ===")
try:
    inf = search_markets("inflation", source="polymarket")
    if not inf.empty:
        for _, row in inf.head(3).iterrows():
            print(f"  {row.get('market_id','?')} | {str(row.get('question','?'))[:60]}")
    else:
        print("  No results")
except Exception as e:
    print(f"  Error: {e}")

print("\n=== VALIDATION COMPLETE ===")
