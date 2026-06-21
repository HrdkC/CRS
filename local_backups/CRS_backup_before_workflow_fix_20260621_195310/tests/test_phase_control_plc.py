from database.recipe_phase_control_manager import (
    RecipePhaseControlManager
)

rows = (
    RecipePhaseControlManager
    .get_phase_control_for_plc(
        1
    )
)

for row in rows:

    print(row)