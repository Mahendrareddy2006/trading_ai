"""Market News Service & API Test Suite.

Verifies:
1. HTML tag cleaning and entity decoding
2. Category tagging (Bitcoin, Ethereum, Altcoins, Regulation, Macro, Exchanges, DeFi)
3. URL validation (only legitimate http/https destinations)
4. Article deduplication by URL and title hash
5. In-memory caching and stale fallback on network failure
6. GET /api/news endpoint contract, filtering, searching, and pagination
7. Public read access without requiring exchange credentials
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from trading_ai.api.app import app
from trading_ai.services.news_service import (
    NewsService, 
    clean_html, 
    validate_url, 
    categorize_article, 
    news_service
)
from trading_ai.api.news import NewsArticleResponse, NewsFeedResponse


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def test_news_service():
    # Return fresh NewsService instance with empty cache for isolated testing
    return NewsService(cache_ttl_seconds=300)


def test_clean_html_and_strip():
    raw = "<p>Bitcoin rallied past <b>$100,000</b> today &amp; set a new high!</p>"
    cleaned = clean_html(raw)
    assert cleaned == "Bitcoin rallied past $100,000 today & set a new high!"
    assert "<p>" not in cleaned
    assert "<b>" not in cleaned


def test_validate_url():
    assert validate_url("https://cointelegraph.com/news/bitcoin-etf") == "https://cointelegraph.com/news/bitcoin-etf"
    assert validate_url("http://coindesk.com/policy/cftc") == "http://coindesk.com/policy/cftc"
    # Disallow invalid schemes
    assert validate_url("javascript:alert(1)") is None
    assert validate_url("file:///etc/passwd") is None
    assert validate_url("ftp://server/file") is None
    assert validate_url("") is None


def test_classify_categories():
    # Bitcoin
    cats_btc = categorize_article("Bitcoin sets new all-time high amid ETF inflows", "BTC trading volume surges", ["crypto"])
    assert "bitcoin" in cats_btc
    assert "all" in cats_btc

    # Ethereum & DeFi
    cats_eth = categorize_article("Ethereum layer 2 TVL expands as Uniswap volume peaks", "DeFi liquidity protocol update", [])
    assert "ethereum" in cats_eth
    assert "defi" in cats_eth

    # Regulation
    cats_reg = categorize_article("SEC and CFTC announce unified crypto enforcement framework", "Regulatory policy shift", [])
    assert "regulation" in cats_reg

    # Macro & Economy
    cats_macro = categorize_article("Federal Reserve rate cuts stimulate risk-on market assets", "Inflation CPI data report", [])
    assert "macro" in cats_macro

    # Exchanges
    cats_exch = categorize_article("Binance reports record futures trading volume", "Exchange orderbook depth", [])
    assert "exchanges" in cats_exch


def test_deduplication(test_news_service):
    # Mock fetch_feed to return items with duplicate titles and URLs
    item1 = {
        "id": "1",
        "title": "Bitcoin Breaks Records",
        "source": "CoinDesk",
        "url": "https://example.com/btc-breaks-records",
        "image_url": None,
        "summary": "Summary text",
        "published_at": "2026-10-11T10:00:00+00:00",
        "categories": ["all", "bitcoin"]
    }
    item2 = {
        "id": "2",
        "title": "bitcoin breaks records",  # Duplicate title case-insensitive
        "source": "Cointelegraph",
        "url": "https://example.com/btc-breaks-records-2",
        "image_url": None,
        "summary": "Duplicate summary",
        "published_at": "2026-10-11T10:05:00+00:00",
        "categories": ["all", "bitcoin"]
    }

    with patch.object(test_news_service, "fetch_feed", side_effect=[[item1], [item2], []]):
        articles = test_news_service.refresh_news(force=True)
        # Should deduplicate down to 1 article
        assert len(articles) == 1
        assert articles[0]["title"] == "Bitcoin Breaks Records"


def test_caching_behavior(test_news_service):
    import time
    # Prime cache
    article = {
        "id": "test_id_1",
        "title": "Institutional Adoption Spikes",
        "source": "Test Source",
        "url": "https://example.com/institutional",
        "image_url": None,
        "summary": "Summary of institutional inflows",
        "published_at": "2026-10-11T12:00:00+00:00",
        "categories": ["all", "bitcoin"]
    }
    test_news_service._cached_articles = [article]
    test_news_service._last_fetch_timestamp = time.time()

    # Request without refresh should hit cache and not call fetch_feed
    with patch.object(test_news_service, "fetch_feed", side_effect=Exception("Should not be called")):
        res = test_news_service.get_news(category="all")
        assert res["total"] == 1
        assert res["is_stale"] is False
        assert res["articles"][0]["id"] == "test_id_1"


def test_stale_fallback_on_network_failure(test_news_service):
    # When cache is expired and network fails, should fall back to cached data marked as stale
    article = {
        "id": "cached_fallback_id",
        "title": "Crypto Market Liquidity Analysis",
        "source": "Test Source",
        "url": "https://example.com/liquidity",
        "image_url": None,
        "summary": "Analysis",
        "published_at": "2026-10-11T10:00:00+00:00",
        "categories": ["all", "macro"]
    }
    test_news_service._cached_articles = [article]
    test_news_service._last_fetch_timestamp = 0  # Force expired

    # Mock fetch_feed returning empty / failure
    with patch.object(test_news_service, "fetch_feed", return_value=[]):
        articles = test_news_service.refresh_news(force=True)
        assert len(articles) == 1
        assert test_news_service._is_stale is True
        assert articles[0]["id"] == "cached_fallback_id"


def test_api_get_news_endpoint(client):
    """Verifies GET /api/news returns 200 with normalized response structure."""
    response = client.get("/api/news?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "articles" in data
    assert "total" in data
    assert "count" in data
    assert "categories" in data
    assert "is_stale" in data
    assert "last_updated" in data
    assert isinstance(data["articles"], list)
    assert len(data["articles"]) <= 5

    if len(data["articles"]) > 0:
        first = data["articles"][0]
        assert "id" in first
        assert "title" in first
        assert "source" in first
        assert "url" in first
        assert first["url"].startswith("http")
        assert "published_at" in first
        assert "categories" in first
        assert isinstance(first["categories"], list)


def test_api_category_and_search_filter(client):
    """Verifies category filtering and search queries work on the endpoint."""
    # Category filter
    res_btc = client.get("/api/news?category=bitcoin&limit=10")
    assert res_btc.status_code == 200
    data_btc = res_btc.json()
    for art in data_btc["articles"]:
        assert "bitcoin" in art["categories"]

    # Search filter
    res_search = client.get("/api/news?search=Bitcoin&limit=5")
    assert res_search.status_code == 200
    data_search = res_search.json()
    for art in data_search["articles"]:
        assert "bitcoin" in art["title"].lower() or "bitcoin" in (art.get("summary") or "").lower()
