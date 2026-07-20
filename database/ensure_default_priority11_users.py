"""Optional secure recovery-user bootstrap.

No passwords are embedded in source. Set the documented CRS_BOOTSTRAP_*_PASSWORD
environment variables before running this module.
"""

from database.upgrade_user_management_priority11 import ensure_priority11_default_users


if __name__ == "__main__":
    ensure_priority11_default_users()
    print("Optional recovery users were created/verified from environment-supplied passwords.")
