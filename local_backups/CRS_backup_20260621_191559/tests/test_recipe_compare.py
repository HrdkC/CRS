from recipe.recipe_compare import (
    RecipeCompare
)

differences = (

    RecipeCompare.compare(

        recipe_1="GT7107",

        recipe_2="PLC_P15KM_20260609_135830"

    )

)

if not differences:

    print(
        "No Differences Found"
    )

else:

    for row in differences:

        print(
            row
        )