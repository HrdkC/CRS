"""Secure one-time CRS administrator bootstrap."""

import argparse
import getpass
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database.user_manager import UserManager
from flask_app.security.password_policy import validate_password_strength


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", default="admin")
    args = parser.parse_args()

    password = getpass.getpass("Temporary administrator password: ")
    confirm = getpass.getpass("Confirm temporary password: ")
    if password != confirm:
        raise SystemExit("Passwords do not match.")
    ok, message = validate_password_strength(password, username=args.username)
    if not ok:
        raise SystemExit(message)

    created = UserManager.create_user(
        username=args.username,
        password=password,
        role="ADMIN",
        created_by="SECURE_BOOTSTRAP",
        password_reset_required=1,
        remarks="Secure one-time administrator bootstrap; reset required on first login.",
    )
    if not created:
        raise SystemExit("Administrator creation failed. The username may already exist.")
    print(f"Administrator created: {args.username}. Password reset is required at first login.")


if __name__ == "__main__":
    main()
