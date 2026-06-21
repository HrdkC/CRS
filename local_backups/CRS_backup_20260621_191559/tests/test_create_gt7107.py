# test_create_gt7107.py

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

RecipeManager.create_recipe(

    recipe_code="GT7107",

    recipe_name="235/60R18 APTERA",

    created_by="admin",

    recipe_description="Production Recipe"

)