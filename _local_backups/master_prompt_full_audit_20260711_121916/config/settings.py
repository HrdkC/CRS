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

# Development fallback only. Production should set CRS_SECRET_KEY.
SECRET_KEY = os.getenv(
    "CRS_SECRET_KEY",
    "crs_secret_key"
)
