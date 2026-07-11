from database.recipe_manager import RecipeManager

recipe_array = RecipeManager.get_recipe_array(

    recipe_code="GT7107",
    version=1

)

print(recipe_array)