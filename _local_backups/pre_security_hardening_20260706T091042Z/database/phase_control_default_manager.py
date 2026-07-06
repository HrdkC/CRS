from database.database import get_connection
from database.phase_template_manager import PhaseTemplateManager


class PhaseControlDefaultManager:
    """Idempotent stage phase-control master seeding.

    Phase-control master data is owned by Machine + Stage. Keeping the defaults
    here avoids route-only setup logic and lets GUI-created stages self-seed.
    """

    FIRST_STAGE_PHASES = [
        "INNERLINER WITH TOPROLL",
        "INNERLINER WITHOUT TOPROLL",
        "PLY 1 WITH TOPROLL",
        "PLY 1 WITHOUT TOPROLL",
        "PLY 2 WITH TOPROLL",
        "PLY 2 WITHOUT TOPROLL",
        "SIDEWALL WITHOUT STITCHER WITH TOPROLL",
        "SIDEWALL WITHOUT STITCHER",
        "RRD WITH CONTOUR STITCHER",
        "RRD WITH CONTOUR & DISK STITCHER",
        "RRD WITH DISK STITCHER",
        "INSERT BEADS",
        "SET BEADS",
        "TURNUPRING",
        "CONTOUR STITCHER",
        "DISK STITCHER",
        "MATERIAL 1 MANUAL",
        "MATERIAL 2 MANUAL",
        "REINFORCEMENT MATERIAL",
        "PLY 3 WITH TOPROLL",
        "PLY 3 WITHOUT TOPROLL",
        "EMPTY PHASE",
    ]

    DEFAULT_GROUPS_BY_STAGE = {
        "FIRST_STAGE": [
            (
                "MAIN",
                "Phase Control",
                "First stage single phase-control group",
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
        ],
    }

    DEFAULT_PHASES_BY_STAGE = {
        "FIRST_STAGE": {
            "MAIN": FIRST_STAGE_PHASES,
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
        },
    }

    @staticmethod
    def _normalize_stage_type(stage_type):
        return str(stage_type or "").strip().upper()

    @staticmethod
    def _is_first_stage(stage_type):
        return (
            PhaseControlDefaultManager._normalize_stage_type(stage_type)
            in {"FIRST_STAGE", "FIRSTSTAGE", "FS"}
        )

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
            cursor.execute(
                """
                UPDATE phase_control_group_master
                SET
                    phase_group_name = ?,
                    description = COALESCE(NULLIF(description, ''), ?),
                    display_order = ?,
                    active = 1
                WHERE id = ?
                """,
                (
                    group_name,
                    description,
                    display_order,
                    row["id"],
                ),
            )
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
        clean_name = PhaseTemplateManager.clean_display_name(phase_name)
        phase_key = PhaseTemplateManager.phase_key(clean_name)
        plc_phase_code = PhaseTemplateManager._phase_code_from_name(
            group_code,
            clean_name,
            display_order,
        )

        cursor.execute(
            """
            SELECT id
            FROM phase_control_master
            WHERE machine_stage_id = ?
                AND UPPER(COALESCE(phase_group_code, '')) = UPPER(?)
                AND UPPER(COALESCE(phase_control_key, phase_control_name)) = UPPER(?)
            """,
            (
                machine_stage_id,
                group_code,
                phase_key,
            ),
        )
        row = cursor.fetchone()
        if row:
            cursor.execute(
                """
                UPDATE phase_control_master
                SET
                    phase_group_name = ?,
                    description = COALESCE(NULLIF(description, ''), ?),
                    plc_phase_code = COALESCE(plc_phase_code, ?)
                WHERE id = ?
                """,
                (
                    group_name,
                    clean_name,
                    plc_phase_code,
                    row["id"],
                ),
            )
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
                phase_control_key,
                plc_phase_code,
                display_order,
                active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                machine_stage_id,
                stage_type,
                group_code,
                group_name,
                clean_name,
                phase_key,
                plc_phase_code,
                display_order,
            ),
        )
        return 1

    @staticmethod
    def _sync_first_stage_single_group(cursor, machine_stage_id, stage_type):
        if not PhaseControlDefaultManager._is_first_stage(stage_type):
            return

        cursor.execute(
            """
            SELECT id
            FROM phase_control_group_master
            WHERE machine_stage_id = ?
                AND UPPER(phase_group_code) = 'MAIN'
            """,
            (machine_stage_id,),
        )
        main_group = cursor.fetchone()
        if main_group:
            cursor.execute(
                """
                UPDATE phase_control_group_master
                SET phase_group_name = 'Phase Control',
                    description = COALESCE(NULLIF(description, ''), 'First stage single phase-control group'),
                    display_order = 1,
                    active = 1
                WHERE id = ?
                """,
                (main_group["id"],),
            )
        else:
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
                VALUES (?, ?, 'MAIN', 'Phase Control', 'First stage single phase-control group', 1, 1)
                """,
                (
                    machine_stage_id,
                    stage_type,
                ),
            )

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM phase_control_master
            WHERE machine_stage_id = ?
                AND UPPER(COALESCE(phase_group_code, 'MAIN')) = 'MAIN'
                AND COALESCE(active, 1) = 1
            """,
            (machine_stage_id,),
        )
        main_option_count = int(cursor.fetchone()["total"] or 0)

        if main_option_count == 0:
            cursor.execute(
                """
                UPDATE phase_control_master
                SET phase_group_code = 'MAIN',
                    phase_group_name = 'Phase Control',
                    active = 1
                WHERE machine_stage_id = ?
                    AND UPPER(COALESCE(phase_group_code, '')) <> 'MAIN'
                """,
                (machine_stage_id,),
            )
        else:
            cursor.execute(
                """
                UPDATE phase_control_master
                SET active = 0
                WHERE machine_stage_id = ?
                    AND UPPER(COALESCE(phase_group_code, '')) <> 'MAIN'
                """,
                (machine_stage_id,),
            )

        cursor.execute(
            """
            UPDATE phase_control_group_master
            SET active = 0
            WHERE machine_stage_id = ?
                AND UPPER(COALESCE(phase_group_code, '')) <> 'MAIN'
            """,
            (machine_stage_id,),
        )

    @staticmethod
    def initialize_for_stage(machine_stage_id, stage_type):
        stage_type = PhaseControlDefaultManager._normalize_stage_type(stage_type)
        groups, phases_by_group = PhaseControlDefaultManager.defaults_for_stage(stage_type)
        if not machine_stage_id or not groups:
            return {
                "groups_added": 0,
                "phases_added": 0,
            }

        PhaseTemplateManager.ensure_schema()

        conn = get_connection()
        cursor = conn.cursor()
        groups_added = 0
        phases_added = 0

        PhaseControlDefaultManager._sync_first_stage_single_group(
            cursor,
            machine_stage_id,
            stage_type,
        )

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
