import sqlite3
from contextlib import contextmanager

from config.settings import (
    DATABASE_PATH,
    SQLITE_BUSY_TIMEOUT_MS,
    SQLITE_JOURNAL_MODE,
    SQLITE_SYNCHRONOUS,
)


def _configure_connection(conn):
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(f"PRAGMA busy_timeout = {max(1000, int(SQLITE_BUSY_TIMEOUT_MS))}")

    # Journal/synchronous PRAGMAs are connection-safe. If the database is on a
    # filesystem that rejects WAL, SQLite returns the effective mode and the app
    # continues with that mode rather than silently changing data semantics.
    try:
        conn.execute(f"PRAGMA journal_mode = {SQLITE_JOURNAL_MODE}").fetchone()
    except sqlite3.DatabaseError:
        pass
    try:
        conn.execute(f"PRAGMA synchronous = {SQLITE_SYNCHRONOUS}")
    except sqlite3.DatabaseError:
        pass
    return conn


def get_connection(*, timeout=None):
    timeout_seconds = (
        float(timeout)
        if timeout is not None
        else max(1.0, SQLITE_BUSY_TIMEOUT_MS / 1000.0)
    )
    conn = sqlite3.connect(
        DATABASE_PATH,
        timeout=timeout_seconds,
    )
    return _configure_connection(conn)


@contextmanager
def transaction(*, immediate=False):
    """Yield one SQLite connection with an explicit atomic transaction."""
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
