from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.models import Base


def make_engine(database_url: str | None = None):
    url = database_url or settings.database_url
    if not url.startswith("sqlite"):
        return create_engine(url)
    # SQLite-specific: :memory: needs StaticPool so every checkout shares
    # the same connection (and thus the same tables/data) instead of each
    # getting its own empty in-memory database.
    is_memory = ":memory:" in url
    kwargs: dict[str, Any] = {"connect_args": {"check_same_thread": False}}
    if is_memory:
        kwargs["poolclass"] = StaticPool
    return create_engine(url, **kwargs)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine)


def init_db(bind=None) -> None:
    Base.metadata.create_all(bind=bind or engine)


def get_session() -> Session:
    return SessionLocal()
