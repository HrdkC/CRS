from database.database import get_connection


class PhaseControlDefaultManager:
    """Idempotent stage phase-control master seeding.

    Phase-control master data is owned by Machine + Stage. Keeping the defaults
    here avoids route-only setup logic and lets GUI-created stages self-seed.
    """

    DEFAULT_GROUPS_BY_STAGE = {
        "FIRST_STAGE": [
            (
                "APPLICATION_SIDE",
                "Application Side",
                "First stage application side phase-control group",
                1,
            ),
        ],
        "SECOND_STAGE": [
            (
                "CAP_STRIP_SIDE",
                "Cap Strip Side",
                "Cap strip side phase-control group",
                1,
            ),
            (
                "BT_SIDE",
                "B&T Side",
                "Belt and tread side phase-control group",
                2,
            ),
            (
                "SHAPING_SIDE",
                "Shaping Side",
                "Shaping side phase-control group",
                3,
            ),
        ],
    }

    DEFAULT_PHASES_BY_STAGE = {
        "FIRST_STAGE": {
            "APPLICATION_SIDE": [
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
                "Empty Phase",
            ],
        },
        "SECOND_STAGE": {
            "CAP_STRIP_SIDE": [
                "Apply CapStrip",
                "Apply Tread",
                "Empty Phase",
            ],
            "BT_SIDE": [
                "Apply Belt 1",
                "Apply Belt 2",
                "Turn Table",
                "Apply Tread",
                "Remove Belt Package",
                "Empty Phase",
            ],
            "SHAPING_SIDE": [
                "Carcass Loader",
                "Preshaping",
                "Stitching Cycle",
                "Remove Cycle",
                "Empty Phase",
            ],
        },
    }

    @staticmethod
    def _normalize_stage_type(stage_type):
        return str(stage_type or "").strip().upper()

    @staticmethod
    def defaults_for_stage(stage_type):
        normalized = PhaseControlDefaultManager._normalize_stage_type(stage_type)
        return (
            PhaseControlDefaultManager.DEFAULT_GROUPS_BY_STAGE.get(normalized, []),
            PhaseControlDefaultManager.DEFAULT_PHASES_BY_STAGE.get(normalized, {}),
        )

    @staticmethod
    def _insert_group_if_missing(
        cursor,
        machine_stage_id,
        stage_type,
        group_code,
        group_name,
        description,
        display_order,
    ):
        cursor.execute(
            """
            SELECT id
            FROM phase_control_group_master
            WHERE machine_stage_id = ?
                AND UPPER(phase_group_code) = UPPER(?)
            """,
            (
                machine_stage_id,
                group_code,
            ),
        )
        row = cursor.fetchone()
        if row:
            return 0

        cursor.execute(
            """
            INSERT INTO phase_control_group_master
            (
                machine_stage_id,
                stage_type,
                phase_group_code,
                phase_group_name,
                description,
                display_order,
                active
            )
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            (
                machine_stage_id,
                stage_type,
                group_code,
                group_name,
                description,
                display_order,
            ),
        )
        return 1

    @staticmethod
    def _insert_phase_if_missing(
        cursor,
        machine_stage_id,
        stage_type,
        group_code,
        group_name,
        phase_name,
        display_order,
    ):
        cursor.execute(
            """
            SELECT id
            FROM phase_control_master
            WHERE machine_stage_id = ?
                AND UPPER(COALESCE(phase_group_code, '')) = UPPER(?)
                AND UPPER(phase_control_name) = UPPER(?)
            """,
            (
                machine_stage_id,
                group_code,
                phase_name,
            ),
        )
        row = cursor.fetchone()
        if row:
            return 0

        cursor.execute(
            """
            INSERT INTO phase_control_master
            (
                machine_stage_id,
                stage_type,
                phase_group_code,
                phase_group_name,
                phase_control_name,
                display_order,
                active
            )
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            (
                machine_stage_id,
                stage_type,
                group_code,
                group_name,
                phase_name,
                display_order,
            ),
        )
        return 1

    @staticmethod
    def initialize_for_stage(machine_stage_id, stage_type):
        stage_type = PhaseControlDefaultManager._normalize_stage_type(stage_type)
        groups, phases_by_group = PhaseControlDefaultManager.defaults_for_stage(stage_type)
        if not machine_stage_id or not groups:
            return {
                "groups_added": 0,
                "phases_added": 0,
            }

        conn = get_connection()
        cursor = conn.cursor()
        groups_added = 0
        phases_added = 0

        for group_code, group_name, description, group_order in groups:
            groups_added += PhaseControlDefaultManager._insert_group_if_missing(
                cursor,
                machine_stage_id,
                stage_type,
                group_code,
                group_name,
                description,
                group_order,
            )
            for phase_order, phase_name in enumerate(
                phases_by_group.get(group_code, []),
                start=1,
            ):
                display_order = (group_order * 100) + phase_order
                phases_added += PhaseControlDefaultManager._insert_phase_if_missing(
                    cursor,
                    machine_stage_id,
                    stage_type,
                    group_code,
                    group_name,
                    phase_name,
                    display_order,
                )

        conn.commit()
        conn.close()

        return {
            "groups_added": groups_added,
            "phases_added": phases_added,
        }

    @staticmethod
    def initialize_for_context(context):
        return PhaseControlDefaultManager.initialize_for_stage(
            context.get("stage_id"),
            context.get("stage_type"),
        )

    @staticmethod
    def initialize_all_stages():
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, stage_type
            FROM machine_stages
            WHERE COALESCE(active, 1) = 1
            """
        )
        stages = [dict(row) for row in cursor.fetchall()]
        conn.close()

        totals = {
            "stages_checked": len(stages),
            "groups_added": 0,
            "phases_added": 0,
        }
        for stage in stages:
            result = PhaseControlDefaultManager.initialize_for_stage(
                stage.get("id"),
                stage.get("stage_type"),
            )
            totals["groups_added"] += result.get("groups_added", 0)
            totals["phases_added"] += result.get("phases_added", 0)

        return totals
