# BABA Around China Economic Data: What Happens?

## What We Studied

Every year in mid-December, China's National Bureau of Statistics (NBS) releases November economic data—things like retail sales, industrial production, and unemployment numbers. This report is a big deal because China is a massive economy, and BABA (Alibaba) is one of China's largest companies.

**The Question:** Does BABA's stock show any consistent patterns around these data releases? Does it get more volatile? Does the price tend to go up or down afterward?

We looked at 5 years of these releases (2020-2024) and analyzed what happened to BABA's stock price before, during, and after each announcement.

---

## Key Findings in Plain English

### 1. **The Event Day Gets Wild**

On the day of the announcement, BABA's daily trading range nearly **doubles** compared to normal days:

- **Normal days (10 days before the event):** Stock moves about 2.7% from low to high
- **Event day:** Stock moves about 4.0% from low to high
- **That's a 49% increase in intraday volatility**

**Translation:** If you're holding BABA on announcement day, expect a wilder ride than usual. The stock swings more dramatically between its high and low points.

---

### 2. **The Stock Tends to Drop During the Day**

On average, BABA opens near the previous day's close (barely any gap), but then **sells off during the trading day**:

- **Mean gap at open:** +0.05% (basically flat)
- **Mean return during the day:** -1.74% (from open to close)

**Translation:** The announcement days have consistently seen selling pressure. The stock tends to finish lower than where it opened, losing about 1.74% on average during the trading session.

---

### 3. **What Happens Over the Next Few Days is Mixed**

After the event, there's no clear "always goes up" or "always goes down" pattern:

| Days After | Average Return | Win Rate | What This Means |
|------------|---------------|----------|-----------------|
| +1 day | -0.06% | 40% (2 out of 5 positive) | Slightly negative, more losers than winners |
| +2 days | +0.49% | 60% (3 out of 5 positive) | Slightly positive, more winners |
| +3 days | -1.50% | 20% (1 out of 5 positive) | Notably negative, mostly losers |
| +5 days | +0.13% | 80% (4 out of 5 positive) | Slightly positive, strong win rate |
| +10 days | -0.63% | 80% (4 out of 5 positive) | Slightly negative BUT most were up |

**Translation:** The stock doesn't have a reliable directional bias after the event. You can't just say "buy it" or "sell it" after the announcement and expect consistent results. The outcomes are all over the place.

---

### 4. **Risk is Real: Bigger Drops Than Gains**

Looking at the 10 days after each event:

- **Best upside (MFE):** +3.70% on average
- **Worst downside (MAE):** -6.83% on average
- **Typical max drawdown:** -5.41%

**Translation:** On average, the stock had more room to fall (-6.83%) than to rise (+3.70%) in the aftermath. If you're wrong, you could lose more than you'd gain if you're right.

---

### 5. **Premarket Goes Crazy**

If you look at just the premarket trading (3:00-8:29 AM Central Time) on event days:

- **Premarket volatility:** 105.8% annualized (extremely high)
- **Regular trading hours volatility:** 30.7% annualized (more normal)

**Translation:** The stock is super jumpy in the premarket session on these days. If you're trading premarket, expect very choppy price action with big swings. Once regular trading hours start, things calm down relatively.

---

## What Does This Mean for Traders/Investors?

### ✅ Things We Can Say with Confidence:

1. **Volatility spikes on the event day** — This is consistent across all 5 events. If you're holding options or planning to trade, expect larger-than-normal moves.

2. **Premarket is chaotic** — The hours before the market opens see huge swings. Don't overreact to premarket moves; they're unusually volatile.

3. **No directional edge** — You can't reliably predict if BABA will go up or down after the announcement. The pattern isn't strong enough.

### ⚠️ Things to Be Cautious About:

1. **Small sample size** — We only have 5 events. One weird year can throw off the averages. These patterns may not hold up with more data.

2. **China is unpredictable** — Different years have different economic contexts. A "good" report one year might not mean the same thing as a "good" report another year.

3. **Other news matters** — These announcements don't happen in a vacuum. Other news (trade wars, regulatory crackdowns, global market crashes) can dominate and make the NBS data release irrelevant.

---

## Practical Takeaways

### If You Own BABA Stock:

- **Expect a bumpier ride on announcement day** — Consider whether you want to hold through it or step aside.
- **Don't assume it'll recover quickly** — The 10-day aftermath has been mixed. Sometimes it bounces back, sometimes it doesn't.

### If You Trade BABA:

- **Volatility traders might find opportunity** — The increased daily range could benefit strategies that profit from movement (like straddles), but be aware of the downside skew.
- **Avoid premarket unless you're experienced** — The volatility before 8:30 AM CT is extreme and can lead to bad fills and unexpected losses.
- **No consistent directional setup** — This isn't an event where you can blindly buy or sell and expect it to work.

### If You're Researching:

- **This is a starting point, not a conclusion** — 5 events isn't enough to build a robust trading strategy. You'd need more years of data and statistical validation.
- **Consider expanding the study** — Look at other Chinese ADRs (JD, PDD, NIO) to see if this is a BABA-specific phenomenon or market-wide.

---

## The Bottom Line

**China NBS November data releases make BABA more volatile, especially during the trading day, but they don't create a reliable directional edge.** The stock tends to sell off intraday on announcement days, but what happens over the following week is inconsistent. 

If you're holding BABA around these dates, be prepared for bigger swings—but don't assume you know which direction it'll go.

---

## About This Study

- **Data:** 5 events from 2020-2024, using Alpaca market data
- **Analysis:** Daily price action for 10 days before and after each event, plus detailed intraday metrics
- **Constraints:** No predictive indicators used—just raw price, volume, and volatility metrics
- **Timezone:** All times in Central Time (CT)

For detailed technical analysis, see the full report: [baba_nbs_study1_report.md](outputs/baba_nbs_study1_report.md)

---

**Study Completed:** December 14, 2025
