import sqlite3
import threading
from contextlib import contextmanager

from config.settings import (
    DATABASE_PATH,
    SQLITE_BUSY_TIMEOUT_MS,
    SQLITE_JOURNAL_MODE,
    SQLITE_SYNCHRONOUS,
)


_JOURNAL_MODE_LOCK = threading.Lock()
_JOURNAL_MODE_INITIALIZED = False


def _initialize_journal_mode_once(conn):
    """Apply the database-level journal mode once per process.

    Re-running ``PRAGMA journal_mode`` on every connection can require an
    exclusive SQLite lock.  The PLC worker and browser status endpoint use
    separate processes, so doing this on every short-lived status read can
    produce transient ``database is locked`` failures.  Journal mode is a
    persistent database property; one startup attempt per process is enough.
    """
    global _JOURNAL_MODE_INITIALIZED

    if _JOURNAL_MODE_INITIALIZED:
        return

    with _JOURNAL_MODE_LOCK:
        if _JOURNAL_MODE_INITIALIZED:
            return
        try:
            conn.execute(f"PRAGMA journal_mode = {SQLITE_JOURNAL_MODE}").fetchone()
        except sqlite3.DatabaseError:
            # The connection still remains usable with SQLite's effective
            # journal mode.  Bootstrap/release validation reports the actual
            # mode separately.
            pass
        finally:
            _JOURNAL_MODE_INITIALIZED = True


def _configure_connection(conn):
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(f"PRAGMA busy_timeout = {max(1000, int(SQLITE_BUSY_TIMEOUT_MS))}")
    _initialize_journal_mode_once(conn)

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
