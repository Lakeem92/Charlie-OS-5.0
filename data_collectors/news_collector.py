"""
QuantLab News Collector
Pulls news using Alpaca (primary) → FMP (fallback) → Tiingo (fallback) → RSS.
Output: catalyst_analysis_db/daily_briefing/news.json
"""
import sys
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

from datetime import datetime, timedelta
from data_collectors.collector_utils import (
    write_output, load_watchlist, safe_api_call, parse_args
)

# ── RSS Feeds ─────────────────────────────────────────────────────────────────
RSS_FEEDS = [
    {'name': 'MarketWatch Top', 'url': 'https://feeds.content.dowjones.io/public/rss/mw_topstories'},
    {'name': 'Reuters Business', 'url': 'https://feeds.reuters.com/reuters/businessNews'},
    {'name': 'CNBC Top', 'url': 'https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114'},
]


# ── Alpaca News (PRIMARY) ────────────────────────────────────────────────────
def _get_alpaca_news(tickers: list[str], limit: int = 50) -> list[dict]:
    """Pull news from Alpaca News API. Returns normalised article dicts."""
    from shared.config.api_clients import LabAlpacaClient
    client = LabAlpacaClient(paper_trading=True)

    if not client.api_key:
        print("    ⚠️ Alpaca API key not set — skipping Alpaca news")
        return []

    all_articles = []
    chunk_size = 20  # Alpaca accepts up to ~50 symbols per call

    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i + chunk_size]
        resp = safe_api_call(
            client.get_news, symbols=chunk, limit=min(limit, 50),
            default={}, label=f'Alpaca news ({len(chunk)} tickers)'
        )
        # Alpaca response: {"news": [article, ...], ...} or a list
        articles = resp.get('news', []) if isinstance(resp, dict) else (resp if isinstance(resp, list) else [])
        for art in articles:
            if not isinstance(art, dict):
                continue
            # Normalise Alpaca fields → common schema
            all_articles.append({
                'title': art.get('headline', ''),
                'url': art.get('url', ''),
                'source': art.get('source', 'Alpaca'),
                'published': art.get('created_at', art.get('updated_at', '')),
                'tickers': art.get('symbols', []),
                'tags': [],
                'description': (art.get('summary') or '')[:300],
            })

    return _dedup_sort(all_articles)


# ── FMP News (FALLBACK 1) ────────────────────────────────────────────────────
def _get_fmp_news(tickers: list[str], limit: int = 50) -> list[dict]:
    """Pull news from FMP stock_news endpoint."""
    from shared.config.api_clients import FMPClient
    client = FMPClient()

    if not client.api_key:
        print("    ⚠️ FMP API key not set — skipping FMP news")
        return []

    all_articles = []
    chunk_size = 20

    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i + chunk_size]
        ticker_str = ','.join(chunk)
        articles = safe_api_call(
            client.get_stock_news, tickers=ticker_str, limit=limit,
            default=[], label=f'FMP news ({len(chunk)} tickers)'
        )
        if isinstance(articles, list):
            for art in articles:
                if not isinstance(art, dict):
                    continue
                all_articles.append({
                    'title': art.get('title', ''),
                    'url': art.get('url', ''),
                    'source': art.get('site', 'FMP'),
                    'published': art.get('publishedDate', ''),
                    'tickers': [art['symbol']] if art.get('symbol') else [],
                    'tags': [],
                    'description': (art.get('text') or '')[:300],
                })

    return _dedup_sort(all_articles)


# ── Tiingo News (FALLBACK 2) ─────────────────────────────────────────────────
def _get_tiingo_news(tickers: list[str], limit: int = 50) -> list[dict]:
    """Pull news from Tiingo."""
    from shared.config.api_clients import TiingoClient
    client = TiingoClient()

    if not client.api_key:
        print("    ⚠️ Tiingo API key not set — skipping Tiingo news")
        return []

    all_articles = []
    chunk_size = 20

    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i + chunk_size]
        ticker_str = ','.join(chunk)
        articles = safe_api_call(
            client.get_news, ticker_str, limit=limit,
            default=[], label=f'Tiingo news ({len(chunk)} tickers)'
        )
        if isinstance(articles, list):
            for art in articles:
                if not isinstance(art, dict):
                    continue
                all_articles.append({
                    'title': art.get('title', ''),
                    'url': art.get('url', ''),
                    'source': art.get('source', 'Tiingo'),
                    'published': art.get('publishedDate', ''),
                    'tickers': art.get('tickers', []),
                    'tags': art.get('tags', []),
                    'description': (art.get('description') or '')[:300],
                })

    return _dedup_sort(all_articles)


# ── RSS (ALWAYS RUNS) ────────────────────────────────────────────────────────
def _get_rss_news() -> list[dict]:
    """Pull general market news from RSS feeds."""
    import feedparser

    articles = []
    for feed_info in RSS_FEEDS:
        feed = safe_api_call(
            feedparser.parse, feed_info['url'],
            default=None, label=f"RSS {feed_info['name']}"
        )
        if feed and feed.get('entries'):
            for entry in feed['entries'][:10]:
                articles.append({
                    'title': entry.get('title', ''),
                    'url': entry.get('link', ''),
                    'source': feed_info['name'],
                    'published': entry.get('published', ''),
                    'tickers': [],
                    'tags': [],
                    'description': (entry.get('summary') or '')[:300],
                })

    return articles


# ── Helpers ───────────────────────────────────────────────────────────────────
def _dedup_sort(articles: list[dict]) -> list[dict]:
    """Deduplicate by URL and sort by published date descending."""
    seen = set()
    unique = []
    for a in articles:
        url = a.get('url', '')
        if url and url not in seen:
            seen.add(url)
            unique.append(a)
    unique.sort(key=lambda x: x.get('published', ''), reverse=True)
    return unique


def _get_news_with_fallback(tickers: list[str], limit: int = 50) -> tuple[list[dict], str]:
    """Try Alpaca → FMP → Tiingo, return (articles, source_used)."""
    articles = _get_alpaca_news(tickers, limit=limit)
    if articles:
        return articles, 'Alpaca'

    articles = _get_fmp_news(tickers, limit=limit)
    if articles:
        return articles, 'FMP'

    articles = _get_tiingo_news(tickers, limit=limit)
    if articles:
        return articles, 'Tiingo'

    return [], 'none'


def collect():
    """Main collection routine."""
    print("📰 News Collector — starting...")
    print("  Source priority: Alpaca → FMP → Tiingo → RSS")

    # Load focus list tickers (priority)
    focus = load_watchlist('focus_list')
    focus_tickers = focus['ticker'].tolist() if 'ticker' in focus.columns else []
    print(f"  Focus list: {len(focus_tickers)} tickers")

    # Load master watchlist (broader)
    master = load_watchlist('master_watchlist')
    master_tickers = master['ticker'].tolist() if 'ticker' in master.columns else []
    print(f"  Master watchlist: {len(master_tickers)} tickers")

    # Pull news for focus list
    print("  Pulling news for focus list...")
    focus_news, focus_src = _get_news_with_fallback(focus_tickers, limit=10) if focus_tickers else ([], 'N/A')
    if focus_tickers:
        print(f"    Source used: {focus_src} ({len(focus_news)} articles)")

    # Pull news for master watchlist
    print("  Pulling news for master watchlist...")
    master_news, master_src = _get_news_with_fallback(master_tickers, limit=5) if master_tickers else ([], 'N/A')
    print(f"    Source used: {master_src} ({len(master_news)} articles)")

    # Pull RSS for general market (always)
    print("  Pulling RSS feeds...")
    rss_news = _get_rss_news()

    output = {
        'focus_news': focus_news[:30],
        'watchlist_news': master_news[:50],
        'market_news': rss_news[:20],
        'sources': {'focus': focus_src, 'watchlist': master_src},
        'counts': {
            'focus': len(focus_news),
            'watchlist': len(master_news),
            'rss': len(rss_news),
        },
    }

    return output


def main():
    args = parse_args('QuantLab News Collector')

    if args.dry_run:
        print("📰 News Collector — DRY RUN")
        focus = load_watchlist('focus_list')
        master = load_watchlist('master_watchlist')
        print(f"  Focus: {len(focus)} tickers | Master: {len(master)} tickers")
        print(f"  RSS feeds: {len(RSS_FEEDS)}")
        print(f"  Source priority: Alpaca → FMP → Tiingo → RSS")
        print(f"  Output: catalyst_analysis_db/daily_briefing/news.json")
        return

    data = collect()
    path = write_output('daily_briefing', 'news.json', data, 'news_collector')
    print(f"  ✅ Written to {path}")


if __name__ == '__main__':
    main()
