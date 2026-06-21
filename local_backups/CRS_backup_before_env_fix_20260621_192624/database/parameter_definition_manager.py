from database.database import (
    get_connection
)


class ParameterDefinitionManager:

    @staticmethod
    def create_parameter(

        machine_id,

        stage_id,

        tag_index,

        plc_array_index,

        parameter_name,

        parameter_class="",

        unit="",

        min_value=None,

        max_value=None,

        default_value=None,

        datatype="REAL",

        english_memo="",

        used=1,

        created_by=None

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id

            FROM parameter_definitions

            WHERE

                machine_id = ?

                AND stage_id = ?

                AND tag_index = ?
            """,
            (
                machine_id,
                stage_id,
                tag_index
            )
        )

        if cursor.fetchone():

            conn.close()

            raise Exception(
                f"Tag Index {tag_index} already exists"
            )

        cursor.execute(
            """
            SELECT id

            FROM parameter_definitions

            WHERE

                machine_id = ?

                AND stage_id = ?

                AND UPPER(parameter_name)
                =
                UPPER(?)
            """,
            (
                machine_id,
                stage_id,
                parameter_name
            )
        )

        if cursor.fetchone():

            conn.close()

            raise Exception(
                f"Parameter {parameter_name} already exists"
            )

        cursor.execute(
            """
            INSERT INTO
            parameter_definitions
            (

                machine_id,

                stage_id,

                tag_index,

                plc_array_index,

                parameter_name,

                parameter_class,

                unit,

                min_value,

                max_value,

                default_value,

                datatype,

                english_memo,

                used,

                created_by

            )
            VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (

                machine_id,

                stage_id,

                tag_index,

                plc_array_index,

                parameter_name.strip().title(),

                parameter_class,

                unit,

                min_value,

                max_value,

                default_value,

                datatype,

                english_memo,

                used,

                created_by

            )
        )

        parameter_definition_id = (
            cursor.lastrowid
        )

        conn.commit()

        conn.close()

        from database.recipe_parameter_value_manager import (
            RecipeParameterValueManager
        )

        RecipeParameterValueManager.create_missing_values(

            machine_id=machine_id,

            stage_id=stage_id,

            parameter_definition_id=parameter_definition_id,

            default_value=default_value

        )

    @staticmethod
    def get_parameters_by_machine_stage(

        machine_id,

        stage_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM parameter_definitions

            WHERE

                machine_id = ?

                AND stage_id = ?

                AND used = 1

            ORDER BY tag_index
            """,
            (
                machine_id,
                stage_id
            )
        )

        rows = cursor.fetchall()

        conn.close()

        return [
            dict(row)
            for row in rows
        ]

    @staticmethod
    def get_all_parameters_by_machine_stage(

        machine_id,

        stage_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM parameter_definitions

            WHERE

                machine_id = ?

                AND stage_id = ?

            ORDER BY tag_index
            """,
            (
                machine_id,
                stage_id
            )
        )

        rows = cursor.fetchall()

        conn.close()

        return [
            dict(row)
            for row in rows
        ]

    @staticmethod
    def search_parameters(

        machine_id,

        stage_id,

        search_text=""

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM parameter_definitions

            WHERE

                machine_id = ?

                AND stage_id = ?

                AND used = 1

                AND
                (
                    UPPER(parameter_name)
                    LIKE
                    UPPER(?)

                    OR

                    CAST(tag_index AS TEXT)
                    LIKE ?
                )

            ORDER BY tag_index
            """,
            (
                machine_id,
                stage_id,
                f"%{search_text}%",
                f"%{search_text}%"
            )
        )

        rows = cursor.fetchall()

        conn.close()

        return [
            dict(row)
            for row in rows
        ]

    @staticmethod
    def get_parameter_by_id(

        parameter_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM parameter_definitions

            WHERE id = ?
            """,
            (
                parameter_id,
            )
        )

        row = cursor.fetchone()

        conn.close()

        if row:

            return dict(row)

        return None

    @staticmethod
    def update_parameter(

        parameter_id,

        parameter_name,

        unit,

        min_value,

        max_value,

        default_value

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE parameter_definitions

            SET

                parameter_name = ?,

                unit = ?,

                min_value = ?,

                max_value = ?,

                default_value = ?,

                updated_at = CURRENT_TIMESTAMP

            WHERE id = ?
            """,
            (
                parameter_name.strip().title(),

                unit,

                min_value,

                max_value,

                default_value,

                parameter_id
            )
        )

        conn.commit()

        conn.close()

    @staticmethod
    def disable_parameter(

        parameter_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE parameter_definitions

            SET

                used = 0,

                updated_at = CURRENT_TIMESTAMP

            WHERE id = ?
            """,
            (
                parameter_id,
            )
        )

        conn.commit()

        conn.close()

    @staticmethod
    def enable_parameter(

        parameter_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE parameter_definitions

            SET

                used = 1,

                updated_at = CURRENT_TIMESTAMP

            WHERE id = ?
            """,
            (
                parameter_id,
            )
        )

        conn.commit()

        conn.close()