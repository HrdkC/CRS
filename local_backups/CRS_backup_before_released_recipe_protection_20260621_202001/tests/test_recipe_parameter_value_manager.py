from database.recipe_parameter_value_manager import (
    RecipeParameterValueManager
)

rows = (

    RecipeParameterValueManager
    .get_recipe_values(

        recipe_id=1

    )

)

print()

print(
    "ROWS =",
    len(rows)
)

print()

for row in rows[:5]:

    print(row)