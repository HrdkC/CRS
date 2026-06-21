import sys
import os

ROOT_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        ".."
    )
)

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from database.recipe_manager import RecipeManager

recipe = RecipeManager.get_recipe(
    "GT7107",
    version=1
)

for row in recipe:

    print(
        row["parameter_name"]
    )