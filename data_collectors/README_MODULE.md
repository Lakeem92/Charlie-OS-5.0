# Data Collectors Module

All data collection scripts for the QuantLab Intelligence Platform.
Each collector pulls from specific APIs and writes structured output
to `catalyst_analysis_db/` and generates dashboard HTML.

## Collectors
| File | Data Sources | Schedule |
|------|-------------|----------|
| `macro_collector.py` | FRED, yfinance, AAII, CFTC | Daily 5:45 AM CT |
| `etf_collector.py` | FINRA, yfinance options, FMP | Daily 5:45 AM CT |
| `ai_cascade_collector.py` | pytrends, SEC EDGAR | Daily 5:45 AM CT |
| `catalyst_collector.py` | Alpaca gaps, FMP earnings, events | Daily 5:45 AM + 6/7/8 AM CT |
| `focus_list_collector.py` | IR scrape, 8-K, Tavily, Form 4 | Daily 5:45 AM CT |
| `commodity_collector.py` | yfinance futures, USDA API | Daily 5:45 AM CT |
| `news_collector.py` | Alpaca, wire RSS, Tavily | Daily 5:45 AM CT |
| `crypto_collector.py` | CoinGecko, Fear & Greed | Daily 5:45 AM CT |

## Usage
All collectors support `--dry-run` flag:
```
python data_collectors/macro_collector.py --dry-run
```
