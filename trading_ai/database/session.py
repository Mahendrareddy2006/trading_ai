"""Database session management and schema initialization."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from trading_ai.config.settings import settings
from trading_ai.database.models import Base

DATABASE_URL = settings.DATABASE_URL
# Normalize postgres:// to postgresql:// for SQLAlchemy 2.0 compatibility on Render
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

is_sqlite = "sqlite" in DATABASE_URL
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine_kwargs = {
    "connect_args": connect_args,
    "echo": settings.DEBUG
}

if not is_sqlite:
    engine_kwargs.update({
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 5,
        "max_overflow": 10
    })

engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


from sqlalchemy import inspect, text

def init_db():
    """Create tables if they do not exist and safely migrate missing columns."""
    Base.metadata.create_all(bind=engine)

    try:
        inspector = inspect(engine)
        if "notification_settings" in inspector.get_table_names():
            columns = [c["name"] for c in inspector.get_columns("notification_settings")]
            new_columns = [
                ("telegram_status", "VARCHAR(30) DEFAULT 'NOT_CONFIGURED'"),
                ("telegram_verified_at", "DATETIME"),
                ("telegram_sender_info", "VARCHAR(255)"),
                ("whatsapp_status", "VARCHAR(30) DEFAULT 'NOT_CONFIGURED'"),
                ("whatsapp_verified_at", "DATETIME"),
                ("whatsapp_sender_info", "VARCHAR(255)"),
                ("whatsapp_api_token", "VARCHAR(500)"),
                ("whatsapp_phone_number_id", "VARCHAR(100)"),
                ("whatsapp_provider", "VARCHAR(50) DEFAULT 'meta'")
            ]
            with engine.connect() as conn:
                for col_name, col_type in new_columns:
                    if col_name not in columns:
                        try:
                            conn.execute(text(f"ALTER TABLE notification_settings ADD COLUMN {col_name} {col_type}"))
                            conn.commit()
                        except Exception:
                            pass
    except Exception:
        pass


def get_db():
    """FastAPI dependency for obtaining a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
