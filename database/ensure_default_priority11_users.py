import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.upgrade_user_management_priority11 import (
    ensure_priority11_default_users
)


if __name__ == "__main__":
    ensure_priority11_default_users()
    print("")
    print("Priority 11 default users ready:")
    print("- operator    / operator123     / OPERATOR     / password reset required")
    print("- engineering / Engineering@123 / ENGINEERING  / password reset required")
    print("- hardik      / Hardik@123      / ADMIN backup / password reset required")
    print("Change all temporary passwords immediately after first login.")
