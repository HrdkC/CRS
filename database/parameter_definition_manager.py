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

        search_text="",

        parameter_scope="active"

    ):

        conn = get_connection()

        cursor = conn.cursor()

        scope_condition = "AND COALESCE(used, 1) = 1"

        if parameter_scope == "inactive":

            scope_condition = "AND COALESCE(used, 1) = 0"

        elif parameter_scope == "all":

            scope_condition = ""

        cursor.execute(
            f"""
            SELECT *

            FROM parameter_definitions

            WHERE

                machine_id = ?

                AND stage_id = ?

                {scope_condition}

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
    def get_usage_counts(

        machine_id,

        stage_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                SUM(
                    CASE
                        WHEN COALESCE(used, 1) = 1
                        THEN 1
                        ELSE 0
                    END
                ) AS active_count,
                SUM(
                    CASE
                        WHEN COALESCE(used, 1) = 0
                        THEN 1
                        ELSE 0
                    END
                ) AS inactive_count,
                COUNT(*) AS total_count

            FROM parameter_definitions

            WHERE
                machine_id = ?
                AND stage_id = ?
            """,
            (
                machine_id,
                stage_id
            )
        )

        row = cursor.fetchone()

        conn.close()

        if not row:

            return {
                "active_count": 0,
                "inactive_count": 0,
                "total_count": 0
            }

        return {
            "active_count": row["active_count"] or 0,
            "inactive_count": row["inactive_count"] or 0,
            "total_count": row["total_count"] or 0
        }

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
    def update_parameter_details(

        parameter_id,

        parameter_name,

        plc_array_index,

        unit,

        min_value,

        max_value,

        default_value,

        used=None

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                machine_id,
                stage_id,
                parameter_name,
                plc_array_index,
                unit,
                min_value,
                max_value,
                default_value,
                COALESCE(used, 1) AS used
            FROM parameter_definitions
            WHERE id = ?
            """,
            (
                parameter_id,
            )
        )

        old_row = cursor.fetchone()

        if not old_row:

            conn.close()

            return None

        old_used = int(
            old_row["used"]
            if old_row["used"] is not None
            else
            1
        )

        new_used = old_used

        if used is not None:

            new_used = 1 if int(used) == 1 else 0

        cursor.execute(
            """
            UPDATE parameter_definitions

            SET

                parameter_name = ?,

                plc_array_index = ?,

                unit = ?,

                min_value = ?,

                max_value = ?,

                default_value = ?,

                used = ?,

                updated_at = CURRENT_TIMESTAMP

            WHERE id = ?
            """,
            (
                parameter_name.strip(),

                plc_array_index,

                unit.strip(),

                min_value,

                max_value,

                default_value,

                new_used,

                parameter_id
            )
        )

        conn.commit()

        conn.close()

        old_detail = dict(old_row)
        old_detail.pop("machine_id", None)
        old_detail.pop("stage_id", None)

        result = {

            "old": old_detail,

            "new": {
                "parameter_name": parameter_name.strip(),
                "plc_array_index": plc_array_index,
                "unit": unit.strip(),
                "min_value": min_value,
                "max_value": max_value,
                "default_value": default_value,
                "used": new_used
            }

        }

        if old_used == 0 and new_used == 1:

            from database.recipe_parameter_value_manager import (
                RecipeParameterValueManager
            )

            RecipeParameterValueManager.create_missing_values(
                machine_id=old_row["machine_id"],
                stage_id=old_row["stage_id"],
                parameter_definition_id=parameter_id,
                default_value=default_value
            )

        return result

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
            SELECT
                machine_id,
                stage_id,
                default_value
            FROM parameter_definitions
            WHERE id = ?
            """,
            (
                parameter_id,
            )
        )

        parameter = cursor.fetchone()

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

        if parameter:

            from database.recipe_parameter_value_manager import (
                RecipeParameterValueManager
            )

            RecipeParameterValueManager.create_missing_values(
                machine_id=parameter["machine_id"],
                stage_id=parameter["stage_id"],
                parameter_definition_id=parameter_id,
                default_value=parameter["default_value"]
            )
