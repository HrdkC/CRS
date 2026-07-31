"""Rollback only the workflow tracking tables; domain configuration is untouched."""

import os
import sys


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from database.database import transaction


def main():
    with transaction(immediate=True) as conn:
        conn.execute("DROP TABLE IF EXISTS configuration_workflow_steps")
        conn.execute("DROP TABLE IF EXISTS configuration_workflows")
        conn.execute(
            "DELETE FROM schema_version WHERE version = ?",
            ("CRS_V13_CONFIGURATION_WORKFLOW_001",),
        )
    print("Configuration workflow rollback: SUCCESS")
    print("Machine, PLC, tag, parameter, phase, recipe, and audit data were not changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
