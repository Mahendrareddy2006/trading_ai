"""User Watchlist & Favorites Router.

Provides:
- Per-user watchlist symbol persistence
- Add / remove favorite market pairs
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from trading_ai.api.deps import get_current_user
from trading_ai.database.models import User, UserWatchlist
from trading_ai.database.session import get_db

watchlist_router = APIRouter(prefix="/api/watchlist", tags=["User Watchlists"])


class WatchlistResponse(BaseModel):
    symbols: List[str]


@watchlist_router.get("", response_model=WatchlistResponse)
def get_user_watchlist(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves user's saved favorite symbols."""
    items = db.query(UserWatchlist).filter(
        UserWatchlist.user_id == current_user.id
    ).all()
    return {"symbols": [i.symbol for i in items]}


@watchlist_router.post("/{symbol}", response_model=WatchlistResponse)
def add_to_watchlist(
    symbol: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Adds a symbol to user's favorites."""
    sym = symbol.upper().strip()
    existing = db.query(UserWatchlist).filter(
        UserWatchlist.user_id == current_user.id,
        UserWatchlist.symbol == sym
    ).first()

    if not existing:
        new_item = UserWatchlist(user_id=current_user.id, symbol=sym)
        db.add(new_item)
        db.commit()

    items = db.query(UserWatchlist).filter(UserWatchlist.user_id == current_user.id).all()
    return {"symbols": [i.symbol for i in items]}


@watchlist_router.delete("/{symbol}", response_model=WatchlistResponse)
def remove_from_watchlist(
    symbol: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Removes a symbol from user's favorites."""
    sym = symbol.upper().strip()
    db.query(UserWatchlist).filter(
        UserWatchlist.user_id == current_user.id,
        UserWatchlist.symbol == sym
    ).delete()
    db.commit()

    items = db.query(UserWatchlist).filter(UserWatchlist.user_id == current_user.id).all()
    return {"symbols": [i.symbol for i in items]}
