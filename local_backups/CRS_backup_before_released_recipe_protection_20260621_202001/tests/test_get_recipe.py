from database.recipe_manager import RecipeManager

recipe = RecipeManager.get_recipe(
    recipe_code="GT7107",
    version=1
)

for row in recipe:
    print(dict(row))