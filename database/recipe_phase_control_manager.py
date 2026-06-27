from database.database import (
    get_connection
)


class RecipePhaseControlManager:

    @staticmethod
    def create_default_phase_rows(

        recipe_id,

        *args,

        **kwargs

    ):

        # recipe_code/machine_id/stage_id may be supplied by newer callers.
        # They are accepted for backward compatibility. Existing first-stage
        # default creation still works exactly as before.

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

        cursor.execute(
            """
            SELECT *

            FROM recipe_phase_control

            WHERE recipe_id = ?

            ORDER BY line_no
            """,
            (
                source_recipe_id,
            )
        )

        rows = cursor.fetchall()

        for row in rows:

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