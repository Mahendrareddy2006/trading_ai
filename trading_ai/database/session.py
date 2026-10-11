"""Database session management and schema initialization."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from trading_ai.config.settings import settings
from trading_ai.database.models import Base

DATABASE_URL = settings.DATABASE_URL
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=settings.DEBUG
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create tables if they do not exist."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency for obtaining a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
