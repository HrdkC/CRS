import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.upgrade_user_management_priority11 import (
    upgrade_user_management_schema,
    ensure_backup_admin_user
)


if __name__ == "__main__":
    upgrade_user_management_schema()
    ensure_backup_admin_user()
    print("Backup admin login ready: username=hardik, temporary password=Hardik@123")
    print("This is a backup super user. Change password immediately after first login.")
