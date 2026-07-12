import os

# config/settings.py

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATABASE_PATH = PROJECT_ROOT / "database" / "recipe.db"

DATABASE_URL = os.getenv(
    "CRS_DATABASE_URL",
    f"sqlite:///{DATABASE_PATH.as_posix()}"
)

RECIPE_EXPORT_FOLDER = PROJECT_ROOT / "recipe_exports"
RECIPE_IMPORT_FOLDER = PROJECT_ROOT / "recipe_imports"

DEFAULT_RECIPE_VERSION = 1

APP_VERSION = os.getenv(
    "CRS_APP_VERSION",
    "1.0 Beta"
)

# Priority 11: security/session configuration
# For plant operator terminals, keep this practical but finite.
SESSION_TIMEOUT_MINUTES = int(
    os.getenv(
        "CRS_SESSION_TIMEOUT_MINUTES",
        "30"
    )
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

    return "crs_secret_key", "development-fallback"


SECRET_KEY, SECRET_KEY_SOURCE = _load_secret_key()
USING_DEVELOPMENT_SECRET = SECRET_KEY_SOURCE == "development-fallback"


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
