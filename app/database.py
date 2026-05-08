from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings


def _normalize_db_url(url: str) -> str:
    """Fuerza el driver psycopg v3 (no psycopg2). Acepta postgresql:// o postgres://."""
    if url.startswith("postgresql+"):
        return url
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


_DB_URL = _normalize_db_url(settings.DATABASE_URL)
_is_local = "localhost" in _DB_URL or "127.0.0.1" in _DB_URL

_engine_kwargs: dict = {"pool_pre_ping": True}
if not _is_local:
    _engine_kwargs["poolclass"] = NullPool

engine = create_engine(_DB_URL, **_engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
