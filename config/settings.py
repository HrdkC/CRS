import os
import secrets
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = Path(
    os.getenv("CRS_DATABASE_PATH", str(PROJECT_ROOT / "database" / "recipe.db"))
).expanduser().resolve()
DATABASE_URL = os.getenv(
    "CRS_DATABASE_URL",
    f"sqlite:///{DATABASE_PATH.as_posix()}"
)

RECIPE_EXPORT_FOLDER = PROJECT_ROOT / "recipe_exports"
RECIPE_IMPORT_FOLDER = PROJECT_ROOT / "recipe_imports"
DEFAULT_RECIPE_VERSION = 1

APP_VERSION = os.getenv("CRS_APP_VERSION", "V11.11-RC1")

SESSION_TIMEOUT_MINUTES = int(
    os.getenv("CRS_SESSION_TIMEOUT_MINUTES", "30")
)

SECRET_KEY_FILE = Path(
    os.getenv(
        "CRS_SECRET_KEY_FILE",
        str(PROJECT_ROOT / "instance" / "crs_secret_key"),
    )
)


def _load_secret_key():
    environment_value = os.getenv("CRS_SECRET_KEY", "").strip()
    if environment_value:
        return environment_value, "environment"

    try:
        file_value = SECRET_KEY_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        file_value = ""

    if file_value:
        return file_value, "file"

    # Never use a predictable fallback. Development sessions are intentionally
    # invalidated on restart until scripts/configure_secret_key.py is run.
    return secrets.token_urlsafe(48), "ephemeral-development"


SECRET_KEY, SECRET_KEY_SOURCE = _load_secret_key()
USING_DEVELOPMENT_SECRET = SECRET_KEY_SOURCE == "ephemeral-development"


def _csv_setting(name):
    return [
        item.strip()
        for item in os.getenv(name, "").split(",")
        if item.strip()
    ]


DEPLOYMENT_MODE = os.getenv(
    "CRS_DEPLOYMENT_MODE",
    "development",
).strip().lower()

TRUSTED_HOSTS = _csv_setting("CRS_TRUSTED_HOSTS")
SECRET_KEY_FALLBACKS = _csv_setting("CRS_SECRET_KEY_FALLBACKS")

# SQLite runtime policy. These settings are centralized so every sqlite3
# connection follows the same durability/concurrency contract.
SQLITE_BUSY_TIMEOUT_MS = int(os.getenv("CRS_SQLITE_BUSY_TIMEOUT_MS", "15000"))
SQLITE_JOURNAL_MODE = os.getenv("CRS_SQLITE_JOURNAL_MODE", "WAL").strip().upper()
SQLITE_SYNCHRONOUS = os.getenv("CRS_SQLITE_SYNCHRONOUS", "FULL").strip().upper()

# Live PLC work is fail-closed. Automated tests and web processes must not
# enable this flag. Only the dedicated supervised worker/manual tools may use it.
ALLOW_LIVE_PLC = os.getenv("CRS_ALLOW_LIVE_PLC_TESTS", "").strip().upper() == "YES"
PLC_WORKER_ENABLED = os.getenv("CRS_PLC_WORKER_ENABLED", "0").strip().lower() in {
    "1", "true", "yes", "on"
}

ALLOW_PLC_COMMUNICATION = os.getenv(
    "CRS_ALLOW_PLC_COMMUNICATION", ""
).strip().upper() == "YES"

ALLOW_LEGACY_RECIPE_WRITES = os.getenv(
    "CRS_ALLOW_LEGACY_RECIPE_WRITES", "0"
).strip().lower() in {"1", "true", "yes", "on"}
