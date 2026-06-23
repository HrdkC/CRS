import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.upgrade_user_management_priority11 import (
    upgrade_user_management_schema,
    ensure_default_operator_user
)


if __name__ == "__main__":
    upgrade_user_management_schema()
    ensure_default_operator_user()
    print("Default operator login ready: username=operator, temporary password=operator123")
    print("Change this password immediately after first login.")
