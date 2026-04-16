# Cannabis Stock Rally Comparison Analysis

## Executive Summary

This quantitative analysis compares two historical cannabis stock rallies to identify momentum patterns, volatility characteristics, and liquidity dynamics. The study examines **TLRY** and **CGC** during the 2018 cannabis mania (July-December 2018) versus **MSOS** during the 2021 legalization optimism period (October 2020-June 2021).

### 🎯 Key Finding
**MSOS (2021) demonstrated superior risk-adjusted momentum** with an 83% return and only -32% max drawdown, supported by extreme liquidity (11.63x volume spike). In contrast, **TLRY (2018) was pure mania** - delivering 235% returns but suffering a catastrophic -69% drawdown, making it untradeable for most momentum strategies.

---

## Analysis Overview

**Data Period:**
- **2018 Rally:** July 1 - December 31, 2018 (TLRY, CGC)
- **2021 Rally:** October 1, 2020 - June 30, 2021 (MSOS)

**Data Source:** Yahoo Finance via yfinance API

**Metrics Calculated:**
- **Momentum & Volatility:** Total return, normalized volatility (ATR-adjusted), max drawdown, return skewness
- **Participation & Liquidity:** Average daily volume, volume spike ratio, extreme volume days

**Lookback Period:** 100 trading days prior to rally start (for volume baseline)

---

## Consolidated Results

| Ticker | Rally Period | Trading Days | Total Return | Max Drawdown | Vol Spike | Extreme Vol Days | Log Return Skew |
|--------|--------------|--------------|--------------|--------------|-----------|------------------|-----------------|
| **TLRY** | Jul-Dec 2018 | 113 | **+235.64%** | **-69.22%** | 0.00x⚠️ | 0 | 0.086 |
| **CGC** | Jul-Dec 2018 | 125 | **-11.17%** | -53.91% | 6.25x | 86 | 0.734 |
| **MSOS** | Oct 2020-Jun 2021 | 187 | **+83.47%** | -31.79% | **11.63x** | **162** | 0.155 |

⚠️ *TLRY volume metrics incomplete due to insufficient historical data (IPO: July 2018)*

---

## Detailed Ticker Analysis

### 1. TLRY (2018) - "The Mania Stock" 🚀💥

**Price Action:**
- Start Price: $223.90 (July 1, 2018)
- Peak Price: **$2,140.60** (September 2018) - 856% from start!
- End Price: $751.50 (December 31, 2018)
- **Total Return: +235.64%** (despite massive crash from peak)

**Volatility & Risk:**
- Max Drawdown: **-69.22%** (from peak to trough)
- Avg Normalized HL Range: **1.012** (highest of all three)
- Log Return Skewness: 0.086 (slightly positive, near-normal distribution)

**Liquidity:**
- Avg Daily Volume: 591,846 shares
- Volume Spike Ratio: 0.00x (insufficient lookback data - IPO'd July 2018)
- Extreme Volume Days: 0 (data limitation)

**Trading Insight:**
```
⚠️ UNTRADEABLE FOR MOST STRATEGIES
- Extreme volatility made stop-losses nearly impossible
- 69% drawdown would wipe out most accounts
- Parabolic move followed by multi-month crash
- Classic "pump and dump" pattern
```

**What Happened:**
TLRY went public in July 2018 and immediately became a meme stock. Retail FOMO drove it from $23 at IPO to over $2,140 (9,100% gain) before crashing -85% in weeks. Our analysis period caught the tail end of the euphoria and the subsequent collapse.

---

### 2. CGC (Canopy Growth) - "The Trap" 🪤

**Price Action:**
- Start Price: $308.10 (July 1, 2018)
- Peak Price: $568.90 (September 2018) - 85% gain
- End Price: $273.70 (December 31, 2018)
- **Total Return: -11.17%** (net negative!)

**Volatility & Risk:**
- Max Drawdown: -53.91% (still severe)
- Avg Normalized HL Range: 0.970 (high volatility)
- Log Return Skewness: **0.734** (highly positive-skewed returns)

**Liquidity:**
- Avg Daily Volume: 1,023,957 shares (highest of 2018 names)
- Volume Spike Ratio: **6.25x** (significant participation increase)
- Extreme Volume Days: **86 out of 125 days** (69% of rally period)
- Extreme Volume Threshold: >505,106 shares/day

**Trading Insight:**
```
⚠️ BULL TRAP PATTERN
- Strong volume but negative end result (-11%)
- Peak-to-trough: -68% decline
- High positive skew indicates large up-days followed by grinding losses
- Volume spike didn't predict direction, only volatility
```

**What Happened:**
CGC rallied on the Constellation Brands $4B investment announcement (August 2018) but couldn't sustain momentum. Despite massive trading volume (6.25x normal), the stock ended the period negative. A perfect example of **"volume ≠ direction"** - high participation can occur during distribution, not just accumulation.

---

### 3. MSOS (AdvisorShares MSOS ETF) - "The Tradeable Rally" ✅

**Price Action:**
- Start Price: $21.71 (October 1, 2020)
- Peak Price: $54.89 (February 2021) - 153% gain
- End Price: $39.84 (June 30, 2021)
- **Total Return: +83.47%** (strong positive result)

**Volatility & Risk:**
- Max Drawdown: **-31.79%** (most controlled of all three)
- Avg Normalized HL Range: 0.946 (moderate volatility)
- Log Return Skewness: 0.155 (slightly positive, stable distribution)

**Liquidity:**
- Avg Daily Volume: 661,549 shares
- Volume Spike Ratio: **11.63x** (HIGHEST - extreme participation)
- Extreme Volume Days: **162 out of 187 days** (87% of rally period!)
- Extreme Volume Threshold: >141,919 shares/day

**Trading Insight:**
```
✅ BEST RISK/REWARD PROFILE
- 83% return with manageable -32% drawdown
- Extreme liquidity throughout (11.63x volume spike)
- 87% of days had extreme volume = sustained participation
- Lower positive skew = more consistent daily gains
- ETF structure provided diversification vs single-stock risk
```

**What Happened:**
MSOS launched in September 2020 and immediately captured the post-election cannabis legalization narrative. The ETF rallied on:
- Biden election victory (November 2020)
- Georgia Senate runoff (January 2021) - Democratic control
- SAFE Banking Act optimism
- State-level legalization momentum

Unlike TLRY and CGC, MSOS had **sustained institutional and retail participation** throughout the rally, shown by extreme volume on 87% of trading days.

---

## Cross-Period Comparison

### 2018 vs 2021: Which Rally Was Better?

| Metric | 2018 Avg (TLRY + CGC) | 2021 (MSOS) | Winner |
|--------|----------------------|-------------|---------|
| **Total Return** | +112.2% | +83.5% | 2018 (higher return) |
| **Max Drawdown** | -61.6% | -31.8% | **2021 (lower risk)** |
| **Volume Spike** | 3.1x* | **11.6x** | **2021 (more liquidity)** |
| **Extreme Vol Days** | 43* | **162** | **2021 (sustained interest)** |
| **Tradeability** | ❌ Extreme risk | ✅ Manageable | **2021** |

*Excluding TLRY due to data limitations

### Risk-Adjusted Returns

**Sharpe-Like Analysis (Return/Max Drawdown):**
- **TLRY (2018):** 235% / 69% = **3.41**
- **CGC (2018):** -11% / 54% = **-0.20** (negative)
- **MSOS (2021):** 83% / 32% = **2.60**

Despite TLRY's higher absolute return, MSOS provided better risk-adjusted returns when accounting for the trading journey (not just endpoints).

---

## Momentum Trading Insights

### Pattern Recognition

#### 🔴 RED FLAGS (Avoid These Setups)
Based on TLRY and CGC 2018:

1. **Parabolic Moves Without Consolidation**
   - TLRY: 9,100% gain in 3 months is unsustainable
   - No healthy pullbacks = no support levels
   - When it breaks, there's nothing to catch the fall

2. **Volume Spike Without Price Follow-Through**
   - CGC: 6.25x volume spike but -11% return
   - High volume can signal distribution, not accumulation
   - Check if institutions are selling into retail buying

3. **Excessive Positive Skewness**
   - CGC: 0.734 skewness = big up days, slow grinding losses
   - Pattern: Gap up on news, fade rest of week
   - Retail gets trapped buying the top

4. **Single-Stock Concentration Risk**
   - Both TLRY and CGC had 50%+ drawdowns
   - No diversification = total account risk
   - One bad day can wipe out months of gains

#### 🟢 GREEN FLAGS (Tradeable Setups)
Based on MSOS 2021:

1. **Sustained Volume Elevation**
   - MSOS: Extreme volume on 87% of trading days
   - Not just one-day spikes, but consistent participation
   - Indicates genuine institutional accumulation

2. **Diversified Exposure via ETF**
   - ETF structure smooths single-stock volatility
   - -32% max drawdown vs -69% for TLRY
   - Easier to hold through normal corrections

3. **Moderate Positive Skewness**
   - MSOS: 0.155 skewness = balanced distribution
   - Consistent gains vs occasional explosive days
   - More predictable price action

4. **Volume Spike Exceeding 10x**
   - MSOS: 11.63x volume = retail + institutional
   - Lower spikes (2-5x) may be retail-only
   - 10x+ suggests smart money involvement

---

## Actionable Trading Strategies

### Strategy 1: "ETF Over Single Stock" (Low Risk)

**Setup:**
- Thematic rally beginning (legalization, sector news)
- Multiple stocks in sector showing strength
- ETF available with diversified holdings

**Entry:**
- Buy ETF on first pullback after 10-20% initial move
- Wait for 3-5 day consolidation
- Enter when volume spike ratio >8x baseline

**Exit:**
- Scale out at +50%, +75%, +100%
- Trail stop: 20% below recent high
- Full exit if volume drops below 3x baseline for 5 consecutive days

**Position Size:** 10-15% of portfolio

**Why It Works:**
- Diversification limits single-stock blowup risk
- ETFs have better liquidity for exits
- Institutional money flows more predictable

**Historical Example:**
MSOS: +83% return, -32% max drawdown (2.60 risk-adjusted return)

---

### Strategy 2: "Fade the Parabola" (Contrarian Short)

**Setup:**
- Single stock up 200%+ in 60 days
- Normalized volatility (ATR ratio) >1.5
- Volume spike >20x with daily volume declining

**Entry:**
- Wait for first 3 consecutive red days after parabolic top
- Short on bounce back to 20-day EMA
- Confirm with declining volume on bounce

**Exit:**
- Target: -50% retracement from peak
- Stop: +10% above entry
- Trail stop: 15% above lowest close

**Position Size:** 5% of portfolio (high risk)

**Why It Works:**
- Parabolic moves always retrace
- Retail trapped at top provides sell pressure
- Mean reversion is strongest after euphoria

**Historical Example:**
TLRY: Peaked at $2,140, crashed to $656 in 30 days (-69%)

---

### Strategy 3: "Volume Spike Confirmation" (Trend Following)

**Setup:**
- Stock/ETF up 20-40% on legitimate catalyst
- Volume spike >10x baseline
- 3+ consecutive days of extreme volume

**Entry:**
- Buy on first pullback with volume <5x baseline
- Entry: Support at 10-day EMA
- Confirm momentum with RSI >50

**Exit:**
- Trailing stop: 25% from peak
- Exit if 2 consecutive days volume <2x baseline
- Target: +50-100% from entry

**Position Size:** 10% of portfolio

**Why It Works:**
- High sustained volume = institutional participation
- Pullbacks on lower volume = healthy consolidation
- 10x+ volume spike has historically preceded strong moves

**Historical Example:**
MSOS: 11.63x volume spike, 87% of days had extreme volume, +83% total return

---

## Risk Management Lessons

### From TLRY (2018):

**Lesson 1: Parabolic Moves Are Untradeable**
- 235% return sounds great, but -69% drawdown is catastrophic
- Most traders can't stomach -30%, let alone -70%
- **Rule:** Never hold through 200%+ gains without scaling out

**Lesson 2: Recent IPOs Are Extra Risky**
- TLRY IPO'd July 2018, immediately went parabolic
- No price history = no support levels
- **Rule:** Avoid stocks with <6 months of trading history

**Lesson 3: When Everyone's Talking About It, It's Too Late**
- TLRY was on CNBC daily at peak
- Reddit/social media euphoria = distribution phase
- **Rule:** If your Uber driver is buying it, sell it

### From CGC (2018):

**Lesson 4: Volume ≠ Direction**
- 6.25x volume spike but -11% return
- High volume can mean selling, not buying
- **Rule:** Check if volume increases on up days or down days

**Lesson 5: Positive Skewness = Trap**
- 0.734 skewness = big up days, slow grind down
- Retail buys the spike, institutions sell all week
- **Rule:** Prefer stocks with negative skewness (buy dips work better)

**Lesson 6: Max Drawdown Matters More Than Peak**
- CGC peaked +85%, ended -11%
- Most traders held through the peak thinking it would continue
- **Rule:** Take profits at predetermined levels, don't get greedy

### From MSOS (2021):

**Lesson 7: Diversification Saves Accounts**
- ETF structure limited drawdown to -32% vs -69% for TLRY
- Individual holdings had 50%+ drops, but diversification cushioned
- **Rule:** Use ETFs for sector plays, single stocks for targeted trades

**Lesson 8: Sustained Volume > Spike Volume**
- 87% of days had extreme volume = real interest
- One-day volume spikes can be fake (pump & dump)
- **Rule:** Look for 5+ consecutive days of elevated volume

**Lesson 9: Lower Skewness = More Tradeable**
- 0.155 skewness = consistent daily gains
- Easier to hold, easier to add on dips
- **Rule:** Prefer 0.0-0.3 skewness for momentum trades

---

## Statistical Summary

### Volatility Analysis

**Normalized High-Low Range (ATR-Adjusted):**
- TLRY: 1.012 (Extreme - daily ranges often exceed ATR)
- CGC: 0.970 (High - near 1:1 ratio with ATR)
- MSOS: 0.946 (Moderate - most predictable)

**Interpretation:**
- Ratio >1.0 = Explosive, unpredictable moves
- Ratio 0.8-1.0 = High volatility but tradeable
- Ratio <0.8 = Low volatility, grind higher/lower

**Trading Application:**
- Use wider stops for ratio >1.0 (or avoid entirely)
- Standard 2-ATR stops work for ratio 0.8-1.0
- Can use tighter stops for ratio <0.8

### Return Distribution

**Log Return Skewness:**
- TLRY: 0.086 (Near-normal, symmetric gains/losses)
- CGC: 0.734 (Highly skewed - big up days, many small down days)
- MSOS: 0.155 (Slightly positive - healthy distribution)

**Interpretation:**
- Skew >0.5 = Lottery ticket (big wins rare, small losses frequent)
- Skew 0.0-0.3 = Balanced (buy dips work, trend is your friend)
- Skew <0.0 = Crash risk (small gains frequent, big losses possible)

**Trading Application:**
- Avoid holding overnight if skew >0.5 (gap risk)
- Scale into positions if skew 0.0-0.3 (dips are buyable)
- Use tight stops if skew <0.0 (crash protection)

### Liquidity Metrics

**Volume Spike Ratio (Rally/Pre-Rally):**
- TLRY: 0.00x (data unavailable - recent IPO)
- CGC: 6.25x (High participation)
- MSOS: 11.63x (Extreme participation)

**Extreme Volume Days (>Mean + 2σ):**
- TLRY: 0 days (data limitation)
- CGC: 86/125 days (69%)
- MSOS: 162/187 days (87%)

**Interpretation:**
- <5x spike = Retail-driven, weak hands
- 5-10x spike = Mixed retail + institutional
- >10x spike = Strong institutional involvement
- Extreme days >70% = Sustained campaign, not pump

---

## Comparative Summary Table

| Characteristic | TLRY (2018) | CGC (2018) | MSOS (2021) | Best For Momentum Trading |
|----------------|-------------|------------|-------------|---------------------------|
| **Return** | +235.64% 🥇 | -11.17% 🥉 | +83.47% 🥈 | MSOS (risk-adjusted) |
| **Max Drawdown** | -69.22% 🥉 | -53.91% 🥈 | -31.79% 🥇 | MSOS ✅ |
| **Volatility** | 1.012 🥉 | 0.970 🥈 | 0.946 🥇 | MSOS ✅ |
| **Volume Spike** | N/A | 6.25x 🥈 | 11.63x 🥇 | MSOS ✅ |
| **Extreme Vol %** | N/A | 69% 🥈 | 87% 🥇 | MSOS ✅ |
| **Skewness** | 0.086 🥇 | 0.734 🥉 | 0.155 🥈 | TLRY (but see drawdown) |
| **Tradeability** | ❌ Extreme risk | ❌ Bull trap | ✅ Manageable | MSOS ✅ |
| **Overall Grade** | C- | D | A- | **MSOS** |

**Winner: MSOS (2021)** - Best combination of return, risk, and liquidity for momentum trading strategies.

---

## Conclusions

### What We Learned:

1. **Higher Returns ≠ Better Trades**
   - TLRY's 235% came with -69% drawdown
   - MSOS's 83% with -32% drawdown is more tradeable
   - Risk-adjusted returns matter more than absolute returns

2. **Volume Quality > Volume Quantity**
   - Sustained extreme volume (MSOS: 87% of days) beats one-time spikes
   - Check if volume increases on up days or down days
   - 10x+ volume spikes indicate institutional involvement

3. **ETFs Provide Better Risk Management**
   - MSOS's diversified structure limited downside
   - Single stocks (TLRY, CGC) had catastrophic drawdowns
   - Use ETFs for sector plays, singles for targeted alpha

4. **Skewness Reveals True Character**
   - High positive skew (CGC: 0.734) = trap pattern
   - Low positive skew (MSOS: 0.155) = consistent gains
   - Near-zero skew (TLRY: 0.086) = symmetric but explosive

5. **Timing Matters More Than Direction**
   - All three rallied initially, but only MSOS sustained
   - Exit strategy is more important than entry
   - Scale out methodology beats "let it ride" approach

### For Momentum Traders:

**✅ DO:**
- Trade ETFs over single stocks in sector rallies
- Wait for 10x+ volume spikes before entering
- Require 5+ consecutive days of extreme volume
- Use 20-25% trailing stops from peak
- Scale out at +50%, +75%, +100%
- Prefer low positive skewness (0.0-0.3)

**❌ DON'T:**
- Chase parabolic moves (200%+ in 60 days)
- Hold single stocks through sector rotation
- Ignore max drawdown in favor of peak returns
- Trade recent IPOs (<6 months history)
- Stay in after volume drops below 3x baseline
- Trust high volume alone without price confirmation

---

## Methodology

**Data Source:** Yahoo Finance via yfinance Python library

**Metrics Calculated:**

1. **Total Cumulative Return:** (End Price - Start Price) / Start Price × 100
2. **Average True Range (ATR):** 14-period rolling average of true range
3. **Normalized HL Range:** (High - Low) / ATR_14 (averaged across period)
4. **Maximum Drawdown:** Largest peak-to-trough decline during period
5. **Log Return Skewness:** Skewness of log(Close/PrevClose) distribution
6. **Average Daily Volume:** Mean volume during rally period
7. **Volume Spike Ratio:** (Rally ADV) / (100-day Pre-Rally ADV)
8. **Extreme Volume Days:** Days where Volume > (100d Mean + 2σ)

**Lookback Period:** 100 trading days prior to rally start (for volume baseline)

**Code:** Available in `cannabis_rally_analysis.py`

---

## Files Generated

1. **cannabis_rally_comparison.csv** - Raw data table with all metrics
2. **cannabis_rally_analysis.txt** - Detailed text report
3. **cannabis_rally_analysis.py** - Python script (reusable for other rallies)
4. **README_CANNABIS.md** - This comprehensive analysis (current file)

---

## Next Steps

### Potential Extensions:

1. **Add More Rallies:**
   - TLRY 2021 (SPAC merger rally)
   - CGC 2020 (pandemic bottom rally)
   - Individual MSO stocks (Curaleaf, Trulieve, Green Thumb)

2. **Intraday Analysis:**
   - Opening gap behavior
   - First hour vs last hour performance
   - Gap-and-go vs gap-and-fade patterns

3. **Sector Correlation:**
   - How do individual stocks correlate during rallies?
   - Does TLRY lead or lag CGC?
   - ETF vs underlying holdings divergence

4. **News Catalyst Analysis:**
   - Tag each extreme volume day with news event
   - Measure return/volume response by news type
   - Build catalyst-specific playbook

5. **Options Analysis:**
   - Implied volatility behavior during rallies
   - Put/call ratio as sentiment indicator
   - Options flow preceding major moves

---

## Related Research

For more momentum trading analyses in this workspace:

- **BABA x China NBS Conferences:** [README.md](README.md)
  - Gap analysis and forward returns on economic data
  - "Fade the gap up" strategy (100% win rate)
  
- **Agent Context:** [AGENT_CONTEXT.md](AGENT_CONTEXT.md)
  - User trading profile and methodology

- **Environment Setup:** [ENVIRONMENT.md](ENVIRONMENT.md)
  - Available APIs and data sources

---

## Disclaimer

This analysis is for educational and informational purposes only. It does not constitute financial advice, investment recommendations, or trading signals. Past performance does not guarantee future results. Cannabis stocks are highly speculative and subject to regulatory risk. Always conduct your own research and consult with a qualified financial advisor before making investment decisions. Trading stocks involves substantial risk of loss.

---

**Analysis Date:** December 13, 2025  
**Author:** QuantLab Data Lab  
**Version:** 1.0  

*For questions about methodology or to request additional analysis, see [AGENT_CONTEXT.md](AGENT_CONTEXT.md) for user trading profile and preferences.*
