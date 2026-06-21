from database.recipe_manager import RecipeManager

RecipeManager.update_parameter(

    recipe_code="GT7107",
    version=1,

    parameter_name="Carcass Setting",

    new_value=390,

    username="admin",

    reason="Trial Update"

)

from database.recipe_manager import RecipeManager

recipe = RecipeManager.get_recipe(
    "GT7107",
    version=1
)

for row in recipe:
    print(
        row["parameter_name"],
        row["parameter_value"]
    )
    
RecipeManager.update_parameter(

    recipe_code="GT7107",
    version=1,

    parameter_name="Carcass Setting",

    new_value=400,

    username="admin",

    reason="Production Trial"
)