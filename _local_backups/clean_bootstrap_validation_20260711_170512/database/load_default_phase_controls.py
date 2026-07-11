from database.phase_control_manager import (
    PhaseControlManager
)

from database.database import (
    get_connection
)


def load_default_phase_controls():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM phase_control_master
        """
    )

    conn.commit()

    conn.close()

    phase_controls = [

        "IL With Toproll",
        "IL Without Toproll",

        "Ply 1 With Toproll",
        "Ply 1 Without Toproll",

        "Ply 2 With Toproll",
        "Ply 2 Without Toproll",

        "Ply 3 With Toproll",
        "Ply 3 Without Toproll",

        "Sidewall With Stitcher",
        "Sidewall Without Stitcher",

        "RRD With Contour Stitcher",
        "RRD With Contour & Disk Stitcher",
        "RRD With Disk Stitcher",

        "Insert Beads",
        "Set Beads",

        "Turnup Ring",

        "Contour Stitcher",

        "Material 1 Manual",
        "Disk Stitcher",
        "Material 2 Manual",

        "Empty Phase"

    ]

    display_order = 1

    for phase_name in phase_controls:

        PhaseControlManager.create_phase_control(

            stage_type="FIRST_STAGE",

            phase_control_name=phase_name,

            description=phase_name,

            display_order=display_order

        )

        display_order += 1

    print(
        f"Loaded {len(phase_controls)} Phase Controls"
    )


if __name__ == "__main__":

    load_default_phase_controls()