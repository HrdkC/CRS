# test_create_recipe.py

from database.recipe_manager import RecipeManager

try:

    RecipeManager.create_recipe(
        recipe_code="GT7107",
        recipe_name="235/60R18 APTERA",
        recipe_description="Production Recipe",
        created_by="admin"
    )

except ValueError as e:

    print(e)