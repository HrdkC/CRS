# test_recipe_status.py

from database.recipe_manager import RecipeManager

RecipeManager.update_recipe_status(

    recipe_code="GT7107",

    status="UNDER_REVIEW",

    username="admin"

)