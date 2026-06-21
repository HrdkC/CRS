# config/settings.py

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATABASE_PATH = PROJECT_ROOT / "database" / "recipe.db"

RECIPE_EXPORT_FOLDER = PROJECT_ROOT / "recipe_exports"

RECIPE_IMPORT_FOLDER = PROJECT_ROOT / "recipe_imports"

DEFAULT_RECIPE_VERSION = 1