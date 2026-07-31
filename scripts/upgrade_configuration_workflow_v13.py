import os
import sys


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from database.configuration_workflow_schema import apply_configuration_workflow_schema
from database.database import get_connection


def main():
    apply_configuration_workflow_schema()
    conn = get_connection()
    try:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = len(conn.execute("PRAGMA foreign_key_check").fetchall())
        workflow_count = conn.execute(
            "SELECT COUNT(*) FROM configuration_workflows"
        ).fetchone()[0]
    finally:
        conn.close()
    print("Configuration workflow migration: SUCCESS")
    print("Schema version                 : CRS_V13_CONFIGURATION_WORKFLOW_001")
    print(f"Workflows backfilled           : {workflow_count}")
    print(f"SQLite integrity               : {integrity}")
    print(f"Foreign-key violations         : {foreign_keys}")
    return 0 if integrity == "ok" and foreign_keys == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

