from database.recipe_manager import RecipeManager

recipes = RecipeManager.list_recipes()

for recipe in recipes:
    print(dict(recipe))