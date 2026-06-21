from database.recipe_manager import RecipeManager

recipe = RecipeManager.get_recipe(

    recipe_code="GT7107",

    version=2

)

for row in recipe:

    print(
        row["parameter_name"],
        row["parameter_value"]
    )