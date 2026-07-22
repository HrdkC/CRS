"""Apply and verify the V13 safe recipe-retention schema migration."""

import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from database.database import get_connection
from database.hardening_schema_manager import (
    RECIPE_RETENTION_SCHEMA_VERSION,
    apply_v11_11_hardening_schema,
)
from database.recipe_retention_manager import RecipeRetentionManager


def main():
    apply_v11_11_hardening_schema()
    if not RecipeRetentionManager.schema_ready():
        raise RuntimeError("Recipe retention migration did not verify successfully.")

    conn = get_connection()
    try:
        version = conn.execute(
            "SELECT version, applied_at FROM schema_version WHERE version=?",
            (RECIPE_RETENTION_SCHEMA_VERSION,),
        ).fetchone()
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_key_issues = len(conn.execute("PRAGMA foreign_key_check").fetchall())
    finally:
        conn.close()

    if str(integrity).lower() != "ok":
        raise RuntimeError(f"SQLite integrity check failed: {integrity}")
    if foreign_key_issues:
        raise RuntimeError(
            f"SQLite foreign-key check found {foreign_key_issues} issue(s)."
        )

    print("Recipe retention migration: SUCCESS")
    print(f"Schema version           : {version['version'] if version else RECIPE_RETENTION_SCHEMA_VERSION}")
    print(f"Applied at               : {version['applied_at'] if version else '-'}")
    print(f"SQLite integrity         : {integrity}")
    print(f"Foreign-key violations   : {foreign_key_issues}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
