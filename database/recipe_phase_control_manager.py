from database.database import (
    get_connection
)


class RecipePhaseControlManager:


    @staticmethod
    def _table_exists(cursor, table_name):
        row = cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        ).fetchone()
        return row is not None

    @staticmethod
    def _columns(cursor, table_name):
        rows = cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {row["name"] for row in rows}

    @staticmethod
    def _create_group_phase_rows(cursor, recipe_id, machine_id, stage_id):
        """
        Create grouped second-stage phase-control rows when group masters exist.
        Example P15 SECOND_STAGE:
          CAP_STRIP_SIDE, BT_SIDE, SHAPING_SIDE.
        """
        if not RecipePhaseControlManager._table_exists(cursor, "phase_control_group_master"):
            return False

        group_count = cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM phase_control_group_master
            WHERE machine_stage_id = ? AND COALESCE(active, 1) = 1
            """,
            (stage_id,)
        ).fetchone()["total"]

        if group_count <= 0:
            return False

        phase_rows = cursor.execute(
            """
            SELECT
                pcm.id AS phase_control_id,
                COALESCE(pcm.phase_group_code, 'MAIN') AS phase_group_code,
                COALESCE(pcm.phase_group_name, 'Phase Control') AS phase_group_name,
                pcm.phase_control_name,
                pcm.display_order,
                g.display_order AS group_order
            FROM phase_control_master pcm
            LEFT JOIN phase_control_group_master g
                ON g.machine_stage_id = pcm.machine_stage_id
                AND g.phase_group_code = pcm.phase_group_code
            WHERE
                pcm.machine_stage_id = ?
                AND COALESCE(pcm.active, 1) = 1
            ORDER BY
                COALESCE(g.display_order, 99),
                COALESCE(pcm.display_order, 0),
                pcm.id
            """,
            (stage_id,)
        ).fetchall()

        if not phase_rows:
            return False

        cols = RecipePhaseControlManager._columns(cursor, "recipe_phase_control")
        has_group_cols = {"phase_group_code", "phase_group_name", "used"}.issubset(cols)
        group_line_counter = {}

        for row in phase_rows:
            group_code = row["phase_group_code"] or "MAIN"
            group_name = row["phase_group_name"] or "Phase Control"
            group_line_counter[group_code] = group_line_counter.get(group_code, 0) + 1
            line_no = group_line_counter[group_code]

            if has_group_cols:
                cursor.execute(
                    """
                    INSERT INTO recipe_phase_control (
                        recipe_id,
                        phase_group_code,
                        phase_group_name,
                        line_no,
                        phase_control_id,
                        stop_option,
                        position_option,
                        sequence_no,
                        used
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (
                        recipe_id,
                        group_code,
                        group_name,
                        line_no,
                        row["phase_control_id"],
                        "No",
                        "No",
                        line_no,
                    )
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO recipe_phase_control (
                        recipe_id,
                        line_no,
                        phase_control_id,
                        stop_option,
                        position_option,
                        sequence_no
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        recipe_id,
                        line_no,
                        row["phase_control_id"],
                        "No",
                        "No",
                        line_no,
                    )
                )

        print(
            f"Grouped phase rows created for Recipe ID {recipe_id}: "
            f"{len(phase_rows)} rows across {len(group_line_counter)} group(s)"
        )
        return True


    @staticmethod
    def create_default_phase_rows(

        recipe_id,

        *args,

        **kwargs

    ):

        # recipe_code/machine_id/stage_id may be supplied by newer callers.
        # First stage keeps old 12-row default behavior.
        # Second stage can create group-wise rows from phase_control_group_master.

        machine_id = kwargs.get("machine_id")
        stage_id = kwargs.get("stage_id")

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(*) AS total

            FROM recipe_phase_control

            WHERE recipe_id = ?
            """,
            (
                recipe_id,
            )
        )

        existing = cursor.fetchone()

        if existing["total"] > 0:

            conn.close()

            print(
                f"Phase Rows Already Exist : "
                f"Recipe ID {recipe_id}"
            )

            return

        if machine_id and stage_id:
            if RecipePhaseControlManager._create_group_phase_rows(
                cursor=cursor,
                recipe_id=recipe_id,
                machine_id=machine_id,
                stage_id=stage_id
            ):
                conn.commit()
                conn.close()
                return

        cursor.execute(
            """
            SELECT id

            FROM phase_control_master

            WHERE phase_control_name =
            'Empty Phase'
            """
        )

        empty_phase = cursor.fetchone()

        if not empty_phase:

            conn.close()

            raise Exception(
                "Empty Phase not found in phase_control_master"
            )

        empty_phase_id = empty_phase["id"]

        for line_no in range(

            1,

            13

        ):

            cursor.execute(
                """
                INSERT INTO
                recipe_phase_control
                (

                    recipe_id,

                    line_no,

                    phase_control_id,

                    stop_option,

                    position_option,

                    sequence_no

                )
                VALUES
                (?, ?, ?, ?, ?, ?)
                """,
                (

                    recipe_id,

                    line_no,

                    empty_phase_id,

                    "No",

                    "No",

                    line_no

                )
            )

        conn.commit()

        conn.close()

        print(
            f"12 Phase Rows Created : "
            f"Recipe ID {recipe_id}"
        )

    @staticmethod
    def get_recipe_phase_control(

        recipe_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cols = RecipePhaseControlManager._columns(cursor, "recipe_phase_control")
        has_group_cols = {"phase_group_code", "phase_group_name"}.issubset(cols)

        if has_group_cols:
            cursor.execute(
                """
                SELECT

                    rpc.*,

                    pcm.phase_control_name,

                    COALESCE(rpc.phase_group_code, 'MAIN') AS phase_group_code,

                    COALESCE(rpc.phase_group_name, 'Phase Control') AS phase_group_name

                FROM
                recipe_phase_control rpc

                LEFT JOIN
                phase_control_master pcm

                ON rpc.phase_control_id = pcm.id

                WHERE

                    rpc.recipe_id = ?

                ORDER BY
                    CASE COALESCE(rpc.phase_group_code, 'MAIN')
                        WHEN 'MAIN' THEN 0
                        WHEN 'CAP_STRIP_SIDE' THEN 1
                        WHEN 'BT_SIDE' THEN 2
                        WHEN 'SHAPING_SIDE' THEN 3
                        ELSE 99
                    END,
                    rpc.line_no
                """,
                (
                    recipe_id,
                )
            )
        else:
            cursor.execute(
                """
                SELECT

                    rpc.*,

                    pcm.phase_control_name

                FROM
                recipe_phase_control rpc

                LEFT JOIN
                phase_control_master pcm

                ON rpc.phase_control_id = pcm.id

                WHERE

                    rpc.recipe_id = ?

                ORDER BY
                    rpc.line_no
                """,
                (
                    recipe_id,
                )
            )

        rows = cursor.fetchall()

        conn.close()

        return [

            dict(row)

            for row in rows

        ]

    @staticmethod
    def update_phase_row(

        phase_row_id,

        phase_control_id,

        stop_option,

        position_option,

        sequence_no

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE
            recipe_phase_control

            SET

                phase_control_id = ?,

                stop_option = ?,

                position_option = ?,

                sequence_no = ?,

                updated_at =
                CURRENT_TIMESTAMP

            WHERE id = ?
            """,
            (

                phase_control_id,

                stop_option,

                position_option,

                sequence_no,

                phase_row_id

            )
        )

        conn.commit()

        conn.close()

    @staticmethod
    def ensure_group_empty_phase_slots(

        recipe_id,

        stage_type,

        stage_id,

        min_slots=6

    ):

        conn = get_connection()

        cursor = conn.cursor()

        if not RecipePhaseControlManager._table_exists(
            cursor,
            "phase_control_group_master"
        ):

            conn.close()

            return

        cols = RecipePhaseControlManager._columns(
            cursor,
            "recipe_phase_control"
        )

        if not {
            "phase_group_code",
            "phase_group_name",
            "used"
        }.issubset(cols):

            conn.close()

            return

        groups = cursor.execute(
            """
            SELECT
                phase_group_code,
                phase_group_name,
                display_order
            FROM phase_control_group_master
            WHERE
                machine_stage_id = ?
                AND COALESCE(active, 1) = 1
            ORDER BY
                display_order,
                phase_group_name
            """,
            (
                stage_id,
            )
        ).fetchall()

        if not groups:

            conn.close()

            return

        for group in groups:

            group_code = group["phase_group_code"] or "MAIN"

            group_name = group["phase_group_name"] or "Phase Control"

            empty_phase = cursor.execute(
                """
                SELECT id
                FROM phase_control_master
                WHERE
                    UPPER(stage_type) = UPPER(?)
                    AND machine_stage_id = ?
                    AND COALESCE(phase_group_code, 'MAIN') = ?
                    AND UPPER(phase_control_name) = 'EMPTY PHASE'
                """,
                (
                    stage_type,
                    stage_id,
                    group_code
                )
            ).fetchone()

            if empty_phase:

                empty_phase_id = empty_phase["id"]

            else:

                cursor.execute(
                    """
                    INSERT INTO phase_control_master
                    (
                        stage_type,
                        machine_stage_id,
                        phase_group_code,
                        phase_group_name,
                        phase_control_name,
                        description,
                        display_order,
                        active
                    )
                    VALUES (?, ?, ?, ?, 'Empty Phase', 'Unused phase-control slot', 999, 1)
                    """,
                    (
                        stage_type,
                        stage_id,
                        group_code,
                        group_name
                    )
                )

                empty_phase_id = cursor.lastrowid

            existing_rows = cursor.execute(
                """
                SELECT line_no
                FROM recipe_phase_control
                WHERE
                    recipe_id = ?
                    AND COALESCE(phase_group_code, 'MAIN') = ?
                """,
                (
                    recipe_id,
                    group_code
                )
            ).fetchall()

            existing_line_numbers = {
                int(row["line_no"])
                for row in existing_rows
                if row["line_no"] is not None
            }

            for line_no in range(1, int(min_slots) + 1):

                if line_no in existing_line_numbers:

                    continue

                cursor.execute(
                    """
                    INSERT INTO recipe_phase_control
                    (
                        recipe_id,
                        phase_group_code,
                        phase_group_name,
                        line_no,
                        phase_control_id,
                        stop_option,
                        position_option,
                        sequence_no,
                        used
                    )
                    VALUES (?, ?, ?, ?, ?, 'No', 'No', ?, 1)
                    """,
                    (
                        recipe_id,
                        group_code,
                        group_name,
                        line_no,
                        empty_phase_id,
                        line_no
                    )
                )

        conn.commit()

        conn.close()

    @staticmethod
    def delete_recipe_phase_control(

        recipe_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE

            FROM recipe_phase_control

            WHERE recipe_id = ?
            """,
            (
                recipe_id,
            )
        )

        conn.commit()

        conn.close()

        print(
            f"Phase Control Deleted : "
            f"Recipe ID {recipe_id}"
        )

    @staticmethod
    def copy_phase_control(

        source_recipe_id,

        target_recipe_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(*) AS total

            FROM recipe_phase_control

            WHERE recipe_id = ?
            """,
            (
                target_recipe_id,
            )
        )

        existing = cursor.fetchone()

        if existing["total"] > 0:

            conn.close()

            print(
                f"Target Recipe Already Has "
                f"Phase Control Rows : "
                f"{target_recipe_id}"
            )

            return

        group_cols = RecipePhaseControlManager._columns(cursor, "recipe_phase_control")
        has_group_cols = {"phase_group_code", "phase_group_name", "used"}.issubset(group_cols)

        cursor.execute(
            """
            SELECT *

            FROM recipe_phase_control

            WHERE recipe_id = ?

            ORDER BY
                CASE COALESCE(phase_group_code, 'MAIN')
                    WHEN 'MAIN' THEN 0
                    WHEN 'CAP_STRIP_SIDE' THEN 1
                    WHEN 'BT_SIDE' THEN 2
                    WHEN 'SHAPING_SIDE' THEN 3
                    ELSE 99
                END,
                line_no
            """,
            (
                source_recipe_id,
            )
        )

        rows = cursor.fetchall()

        for row in rows:

            if has_group_cols:
                cursor.execute(
                    """
                    INSERT INTO
                    recipe_phase_control
                    (

                        recipe_id,

                        phase_group_code,

                        phase_group_name,

                        line_no,

                        phase_control_id,

                        stop_option,

                        position_option,

                        sequence_no,

                        used

                    )
                    VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (

                        target_recipe_id,

                        row["phase_group_code"],

                        row["phase_group_name"],

                        row["line_no"],

                        row["phase_control_id"],

                        row["stop_option"],

                        row["position_option"],

                        row["sequence_no"],

                        row["used"] if "used" in row.keys() else 1

                    )
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO
                    recipe_phase_control
                    (

                        recipe_id,

                        line_no,

                        phase_control_id,

                        stop_option,

                        position_option,

                        sequence_no

                    )
                    VALUES
                    (?, ?, ?, ?, ?, ?)
                    """,
                    (

                        target_recipe_id,

                        row["line_no"],

                        row["phase_control_id"],

                        row["stop_option"],

                        row["position_option"],

                        row["sequence_no"]

                    )
                )

        conn.commit()

        conn.close()

        print(
            f"Phase Control Copied : "
            f"{source_recipe_id} -> "
            f"{target_recipe_id}"
        )

    @staticmethod
    def get_phase_control_for_plc(

        recipe_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT

                rpc.line_no,

                pcm.phase_control_name,

                rpc.stop_option,

                rpc.position_option

            FROM
            recipe_phase_control rpc

            LEFT JOIN
            phase_control_master pcm

            ON rpc.phase_control_id = pcm.id

            WHERE
                rpc.recipe_id = ?

            ORDER BY
                rpc.line_no
            """,
            (
                recipe_id,
            )
        )

        rows = cursor.fetchall()

        conn.close()

        return [

            dict(row)

            for row in rows

        ]
