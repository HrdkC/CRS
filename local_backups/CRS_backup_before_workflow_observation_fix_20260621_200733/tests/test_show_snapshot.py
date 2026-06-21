from database.recipe_manager import (
    RecipeManager
)

recipe = RecipeManager.get_recipe(

    "PLC_P15KM_20260609_135004"

)

print()

print(
    "Parameter Count =",
    len(recipe)
)

print()

for row in recipe:

    print(
        dict(row)
    )