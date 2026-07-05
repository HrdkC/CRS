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

from database.recipe_approval_manager import (
    RecipeApprovalManager
)

from database.recipe_manager import (
    RecipeManager
)

from database.recipe_status_history_manager import (
    RecipeStatusHistoryManager
)


RECIPE_ID = 1

print(
    "\nCurrent Recipe:\n"
)

recipe = (
    RecipeManager
    .get_recipe_by_id(
        RECIPE_ID
    )
)

print(recipe)

print(
    "\nSubmitting For Review...\n"
)

result = (
    RecipeApprovalManager
    .submit_for_review(

        recipe_id=
        RECIPE_ID,

        username=
        "production"

    )
)

print(result)

print(
    "\nApproving Recipe...\n"
)

result = (
    RecipeApprovalManager
    .approve_recipe(

        recipe_id=
        RECIPE_ID,

        username=
        "technology",

        remarks=
        "Recipe Verified"
    )
)

print(result)

print(
    "\nRecipe After Approval:\n"
)

recipe = (
    RecipeManager
    .get_recipe_by_id(
        RECIPE_ID
    )
)

print(recipe)

print(
    "\nWorkflow History:\n"
)

history = (
    RecipeStatusHistoryManager
    .get_history(
        RECIPE_ID
    )
)

for row in history:

    print(row)
    