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

from database.recipe_validation_manager import (
    RecipeValidationManager
)


recipe_id = 1

result = (
    RecipeValidationManager
    .validate_recipe(
        recipe_id
    )
)

print()

print(
    "VALID :",
    result["valid"]
)

print()

for error in result["errors"]:

    print(
        error
    )