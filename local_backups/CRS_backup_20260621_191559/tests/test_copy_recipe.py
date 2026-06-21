import sys
import os

ROOT_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        ".."
    )
)

if ROOT_DIR not in sys.path:

    sys.path.insert(
        0,
        ROOT_DIR
    )

from database.recipe_manager import (
    RecipeManager
)

result = (
    RecipeManager.copy_recipe(

        source_recipe_id=1,

        new_recipe_code=
        "GT_TEST_002",

        new_recipe_name=
        "Copied Recipe",

        username=
        "admin"

    )
)

print(result)