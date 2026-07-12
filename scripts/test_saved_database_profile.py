"""Test the DPAPI-protected MySQL profile without starting Flask."""

import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database.database_configuration_manager import DatabaseConfigurationManager


def main():
    result = DatabaseConfigurationManager.test_saved_profile()
    if not result.get("ok"):
        print("Saved MySQL profile test: FAILED")
        for error in result.get("errors") or []:
            print(f"- {error}")
        return 1

    print("Saved MySQL profile test: PASSED")
    print(f"Server version: {result['server_version']}")
    print(f"Database: {result['database_name']}")
    print(f"Authenticated account: {result['authenticated_user']}")
    print(f"Response time: {result['elapsed_ms']} ms")
    print("Password: [protected by Windows DPAPI]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

