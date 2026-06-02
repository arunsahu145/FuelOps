"""
Petrol Pump Finance Manager ERP — Database Engine
SQLAlchemy engine configuration and session management.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from config import DATABASE_URL

# ─── SQLAlchemy Engine ────────────────────────────────────────────────────────
# Using check_same_thread=False for SQLite since FastAPI uses thread pools
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,  # Set True for SQL debugging
    pool_pre_ping=True,
)

# Enable WAL mode and foreign keys for SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# ─── Session Factory ─────────────────────────────────────────────────────────
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ─── Base Class for Models ───────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ─── Dependency for FastAPI routes ───────────────────────────────────────────
def get_db():
    """Yield a database session for each request, auto-close on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables defined in models."""
    from database import models  # noqa: F401 — import to register models
    Base.metadata.create_all(bind=engine)
