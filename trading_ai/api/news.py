"""Market News API Router.

Provides:
- GET /api/news: paginated, categorized, searchable live cryptocurrency news
- Upstream feed aggregation from Cointelegraph, CoinDesk, and Decrypt
- Non-blocking in-memory cache with fallback on external failure
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from trading_ai.services.news_service import news_service

news_router = APIRouter(prefix="/api/news", tags=["Market News"])


class NewsArticleResponse(BaseModel):
    id: str
    title: str
    source: str
    url: str
    image_url: Optional[str] = None
    summary: str
    published_at: str
    categories: List[str]
    is_important: bool = False
    urgency: str = "NORMAL"
    importance_reason: Optional[str] = None


class NewsFeedResponse(BaseModel):
    status: str
    total: int
    count: int
    limit: int
    offset: int
    category: str
    categories: List[str]
    last_updated: str
    is_stale: bool
    articles: List[NewsArticleResponse]


@news_router.get("", response_model=NewsFeedResponse)
def get_market_news(
    category: str = Query("all", description="Filter by category: all, bitcoin, ethereum, altcoins, regulation, macro, exchanges, defi"),
    search: Optional[str] = Query(None, description="Search term in headline or summary"),
    source: Optional[str] = Query(None, description="Filter by publisher name"),
    limit: int = Query(20, ge=1, le=100, description="Max items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    refresh: bool = Query(False, description="Force fresh fetch bypassing cache")
):
    """Returns curated, verified cryptocurrency market news headlines from Tier-1 sources."""
    if refresh:
        news_service.refresh_news(force=True)

    result = news_service.get_news(
        category=category,
        search=search,
        source=source,
        limit=limit,
        offset=offset
    )
    return result
