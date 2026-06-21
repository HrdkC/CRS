from database.recipe_phase_control_manager import (
    RecipePhaseControlManager
)

from database.database import (
    get_connection
)

recipe_id = 1

RecipePhaseControlManager.create_default_phase_rows(
    recipe_id
)

conn = get_connection()

cursor = conn.cursor()

cursor.execute(
    """
    SELECT *

    FROM recipe_phase_control

    WHERE recipe_id = 1
    """
)

rows = cursor.fetchall()

print(
    "ROWS =",
    len(rows)
)

for row in rows:

    print(
        dict(row)
    )

conn.close()