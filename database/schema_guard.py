"""Read-only runtime schema preflight helpers."""

from database.database import get_connection


def require_table(table_name, required_columns=()):
    conn = get_connection()
    try:
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        ).fetchone()
        if not exists:
            raise RuntimeError(
                f"Required CRS table '{table_name}' is missing. "
                "Stop the service and run the controlled bootstrap/migrations."
            )
        columns = {
            row[1] for row in conn.execute(f"PRAGMA table_info({table_name})")
        }
        missing = sorted(set(required_columns) - columns)
        if missing:
            raise RuntimeError(
                f"CRS table '{table_name}' is missing columns: {', '.join(missing)}. "
                "Stop the service and run the controlled migrations."
            )
    finally:
        conn.close()
    return True


def require_tables(specification):
    for table_name, columns in specification.items():
        require_table(table_name, columns)
    return True
