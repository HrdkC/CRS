from database.phase_control_manager import (
    PhaseControlManager
)

PhaseControlManager.create_phase_control(

    stage_type="FIRST_STAGE",

    phase_control_name="Application Side",

    description="First Stage Application Sequence",

    display_order=1

)

PhaseControlManager.create_phase_control(

    stage_type="SECOND_STAGE",

    phase_control_name="Cap Strip Side",

    description="Cap Strip Application Sequence",

    display_order=1

)

PhaseControlManager.create_phase_control(

    stage_type="SECOND_STAGE",

    phase_control_name="B&T Side",

    description="B&T Application Sequence",

    display_order=2

)

PhaseControlManager.create_phase_control(

    stage_type="SECOND_STAGE",

    phase_control_name="Shaping Side",

    description="Shaping Application Sequence",

    display_order=3

)

print("Standard Phase Controls Seeded")