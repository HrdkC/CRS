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
