"""
Check shares outstanding and float for TLRY vs CGC during 2018 rally.
"""

import yfinance as yf

print("=" * 70)
print("TLRY vs CGC - Float Comparison (2018)")
print("=" * 70)

# Get ticker info
tlry = yf.Ticker("TLRY")
cgc = yf.Ticker("CGC")

print("\n📊 TLRY (2018 IPO):")
print(f"  Current Shares Outstanding: {tlry.info.get('sharesOutstanding', 'N/A'):,}")
print(f"  Current Float: {tlry.info.get('floatShares', 'N/A'):,}")
print(f"  IPO Date: July 19, 2018")

print("\n📊 CGC (Public since 2014):")
print(f"  Current Shares Outstanding: {cgc.info.get('sharesOutstanding', 'N/A'):,}")
print(f"  Current Float: {cgc.info.get('floatShares', 'N/A'):,}")

# Get historical volume comparison (proxy for liquidity)
print("\n" + "=" * 70)
print("Average Daily Volume During 2018 Rally:")
print("=" * 70)

tlry_hist = yf.download("TLRY", start="2018-07-01", end="2018-12-31", progress=False)
cgc_hist = yf.download("CGC", start="2018-07-01", end="2018-12-31", progress=False)

if not tlry_hist.empty:
    tlry_avg_vol = float(tlry_hist['Volume'].mean())
    print(f"\nTLRY Avg Volume: {int(tlry_avg_vol):,} shares/day")
else:
    print("\nTLRY: No volume data available")
    tlry_avg_vol = None

if not cgc_hist.empty:
    cgc_avg_vol = float(cgc_hist['Volume'].mean())
    print(f"CGC Avg Volume:  {int(cgc_avg_vol):,} shares/day")
else:
    print("CGC: No volume data available")
    cgc_avg_vol = None

if tlry_avg_vol and cgc_avg_vol:
    ratio = cgc_avg_vol / tlry_avg_vol
    print(f"\n💡 CGC traded {ratio:.2f}x more volume than TLRY")

print("\n" + "=" * 70)
print("\n🔍 Historical Context (2018):")
print("=" * 70)
print("""
TLRY (Tilray):
- IPO'd July 19, 2018 at $17/share (raised $153M)
- Initial float was TINY: ~9-10 million shares
- 75% locked up by insiders/early investors (180-day lockup)
- Retail could only trade ~2-3 million shares initially
- This created the "short squeeze" dynamic

CGC (Canopy Growth):
- Public since 2014 (TSX), MUCH larger float
- Estimated ~200-300 million shares outstanding in 2018
- Better liquidity, more institutional ownership
- Still volatile, but not "meme stock" level

Result:
TLRY's tiny float + lockup period = rocket fuel for volatility
Same buying pressure on TLRY moved it 10x more than CGC
""")
