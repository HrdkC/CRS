from database.recipe_manager import (
    RecipeManager
)

for recipe in RecipeManager.list_recipes():

    print(
        recipe["recipe_code"]
    )