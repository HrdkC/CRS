from database.recipe_manager import RecipeManager

recipe = RecipeManager.get_recipe(

    recipe_code="GT7200",

    version=1

)

for row in recipe:

    print(
        row["parameter_name"],
        row["parameter_value"]
    )