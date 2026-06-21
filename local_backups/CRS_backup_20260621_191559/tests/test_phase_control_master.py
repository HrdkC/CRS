from database.phase_control_manager import (
    PhaseControlManager
)

rows = (

    PhaseControlManager
    .get_phase_controls_by_stage(

        "FIRST_STAGE"

    )

)

print(
    "TOTAL =",
    len(rows)
)

for row in rows:

    print(
        row["display_order"],
        row["phase_control_name"]
    )