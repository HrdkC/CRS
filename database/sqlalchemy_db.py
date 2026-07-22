from contextlib import contextmanager

from sqlalchemy import (
    create_engine,
    event,
    text,
)
from sqlalchemy.engine import make_url
from sqlalchemy.orm import (
    declarative_base,
    scoped_session,
    sessionmaker,
)

from config.settings import (
    DATABASE_URL,
    SQLITE_BUSY_TIMEOUT_MS,
    SQLITE_SYNCHRONOUS,
)


def build_connect_args():
    url = make_url(DATABASE_URL)

    if url.drivername.startswith("sqlite"):
        return {
            "check_same_thread": False,
            "timeout": max(1.0, SQLITE_BUSY_TIMEOUT_MS / 1000.0),
        }

    return {}


engine = create_engine(
    DATABASE_URL,
    future=True,
    pool_pre_ping=True,
    connect_args=build_connect_args(),
)


if make_url(DATABASE_URL).drivername.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _configure_sqlite_connection(dbapi_connection, _connection_record):
        """Keep SQLAlchemy connections aligned with direct sqlite3 access.

        ``journal_mode`` is intentionally not changed here because it is a
        database-level setting and can require an exclusive lock.  The direct
        database helper initializes it once per process; these connection-local
        PRAGMAs are safe on every pooled connection.
        """
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute(
                f"PRAGMA busy_timeout = {max(1000, int(SQLITE_BUSY_TIMEOUT_MS))}"
            )
            cursor.execute(f"PRAGMA synchronous = {SQLITE_SYNCHRONOUS}")
        finally:
            cursor.close()


SessionLocal = scoped_session(
    sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )
)

Base = declarative_base()


@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        SessionLocal.remove()


def remove_session():
    SessionLocal.remove()


def check_connection():
    with engine.connect() as connection:
        return connection.execute(text("SELECT 1")).scalar_one()
