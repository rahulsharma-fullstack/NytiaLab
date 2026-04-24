"""Database engine and session management."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    pass


# Create the engine (connection pool to Postgres)
engine = create_engine(
    settings.database_url,
    echo=False,  # Set to True to see all SQL queries in logs (useful for debugging)
    pool_pre_ping=True,  # Verify connections are alive before using them
)

# Session factory — each request gets its own session
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a DB session.

    Usage in a router:
        def my_endpoint(db: Session = Depends(get_db)):
            ...

    Automatically commits on success, rolls back on exception, closes on exit.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()