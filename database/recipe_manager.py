# database/recipe_manager.py

from database.database import get_connection
from database.audit_manager import AuditManager


class RecipeManager:

    @staticmethod
    def create_recipe(

        machine_id,

        stage_id,

        recipe_code,

        recipe_name,

        created_by

    ):

        from database.recipe_parameter_value_manager import (
            RecipeParameterValueManager
        )
        
        from database.recipe_phase_control_manager import (
            RecipePhaseControlManager
        )

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM parameter_definitions
            WHERE machine_id = ? AND stage_id = ? AND COALESCE(used, 1) = 1
            """,
            (machine_id, stage_id)
        )
        parameter_count = cursor.fetchone()["total"]
        if parameter_count <= 0:
            conn.close()
            raise ValueError(
                "Parameter master is not configured for this machine/stage. "
                "Build/import parameter definitions before creating recipe."
            )

        cursor.execute(
            """
            INSERT INTO recipes
            (

                machine_id,

                stage_id,

                recipe_code,

                recipe_name,

                created_by

            )
            VALUES
            (?, ?, ?, ?, ?)
            """,
            (
                machine_id,

                stage_id,

                recipe_code.upper(),

                recipe_name,

                created_by
            )
        )

        recipe_id = cursor.lastrowid

        conn.commit()

        conn.close()

        RecipeParameterValueManager.create_values_from_template(

            recipe_id=recipe_id,

            machine_id=machine_id,

            stage_id=stage_id

        )
        
        RecipePhaseControlManager.create_default_phase_rows(

            recipe_id=recipe_id,

            recipe_code=recipe_code.upper(),

            machine_id=machine_id,

            stage_id=stage_id

        )

        return recipe_id

    @staticmethod
    def get_recipes(

        machine_id,

        stage_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT

                r.*,

                CASE
                    WHEN
                        r.status = 'RELEASED'

                        AND r.version = (
                            SELECT MAX(x.version)

                            FROM recipes x

                            WHERE
                                x.machine_id = r.machine_id

                                AND x.stage_id = r.stage_id

                                AND UPPER(x.recipe_code) = UPPER(r.recipe_code)

                                AND x.status = 'RELEASED'
                        )

                    THEN 1

                    ELSE 0

                END AS is_current_released,

                CASE
                    WHEN
                        r.status = 'RELEASED'

                        AND r.version = (
                            SELECT MAX(x.version)

                            FROM recipes x

                            WHERE
                                x.machine_id = r.machine_id

                                AND x.stage_id = r.stage_id

                                AND UPPER(x.recipe_code) = UPPER(r.recipe_code)

                                AND x.status = 'RELEASED'
                        )

                    THEN 'CURRENT_RELEASED'

                    WHEN r.status = 'RELEASED'

                    THEN 'HISTORY_RELEASED'

                    WHEN
                        r.status = 'DRAFT'

                        AND EXISTS (
                            SELECT 1

                            FROM recipes x

                            WHERE
                                x.machine_id = r.machine_id

                                AND x.stage_id = r.stage_id

                                AND UPPER(x.recipe_code) = UPPER(r.recipe_code)

                                AND x.version < r.version

                                AND x.status = 'RELEASED'
                        )

                    THEN 'DRAFT_REVISION'

                    ELSE r.status

                END AS version_usage_status

            FROM recipes r

            WHERE

                machine_id = ?

                AND stage_id = ?

            ORDER BY
                recipe_code,
                version DESC
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
    def list_recipes(machine_id=None, stage_id=None):

        conn = get_connection()

        cursor = conn.cursor()

        where_clauses = []
        params = []

        if machine_id is not None:
            where_clauses.append("r.machine_id = ?")
            params.append(machine_id)

        if stage_id is not None:
            where_clauses.append("r.stage_id = ?")
            params.append(stage_id)

        where_sql = ""
        if where_clauses:
            where_sql = " WHERE " + " AND ".join(where_clauses)

        cursor.execute(
            f"""
            SELECT

                r.*,

                CASE
                    WHEN
                        r.status = 'RELEASED'

                        AND r.version = (
                            SELECT MAX(x.version)

                            FROM recipes x

                            WHERE
                                x.machine_id = r.machine_id

                                AND x.stage_id = r.stage_id

                                AND UPPER(x.recipe_code) = UPPER(r.recipe_code)

                                AND x.status = 'RELEASED'
                        )

                    THEN 1

                    ELSE 0

                END AS is_current_released,

                CASE
                    WHEN
                        r.status = 'RELEASED'

                        AND r.version = (
                            SELECT MAX(x.version)

                            FROM recipes x

                            WHERE
                                x.machine_id = r.machine_id

                                AND x.stage_id = r.stage_id

                                AND UPPER(x.recipe_code) = UPPER(r.recipe_code)

                                AND x.status = 'RELEASED'
                        )

                    THEN 'CURRENT_RELEASED'

                    WHEN r.status = 'RELEASED'

                    THEN 'HISTORY_RELEASED'

                    WHEN
                        r.status = 'DRAFT'

                        AND EXISTS (
                            SELECT 1

                            FROM recipes x

                            WHERE
                                x.machine_id = r.machine_id

                                AND x.stage_id = r.stage_id

                                AND UPPER(x.recipe_code) = UPPER(r.recipe_code)

                                AND x.version < r.version

                                AND x.status = 'RELEASED'
                        )

                    THEN 'DRAFT_REVISION'

                    ELSE r.status

                END AS version_usage_status,

                m.machine_code,

                s.stage_type

            FROM recipes r

            LEFT JOIN tbm_machines m

                ON r.machine_id = m.id

            LEFT JOIN machine_stages s

                ON r.stage_id = s.id

            {where_sql}

            ORDER BY
                r.recipe_code,
                r.version DESC
            """,
            params
        )

        rows = cursor.fetchall()

        conn.close()

        return [
            dict(row)
            for row in rows
        ]
        

    @staticmethod
    def copy_recipe(

        source_recipe_id,

        new_recipe_code,

        new_recipe_name,

        username

    ):

        from database.recipe_status_history_manager import (
            RecipeStatusHistoryManager
        )

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT

                r.*,

                CASE
                    WHEN
                        r.status = 'RELEASED'

                        AND r.version = (
                            SELECT MAX(x.version)

                            FROM recipes x

                            WHERE
                                x.machine_id = r.machine_id

                                AND x.stage_id = r.stage_id

                                AND UPPER(x.recipe_code) = UPPER(r.recipe_code)

                                AND x.status = 'RELEASED'
                        )

                    THEN 1

                    ELSE 0

                END AS is_current_released,

                CASE
                    WHEN
                        r.status = 'RELEASED'

                        AND r.version = (
                            SELECT MAX(x.version)

                            FROM recipes x

                            WHERE
                                x.machine_id = r.machine_id

                                AND x.stage_id = r.stage_id

                                AND UPPER(x.recipe_code) = UPPER(r.recipe_code)

                                AND x.status = 'RELEASED'
                        )

                    THEN 'CURRENT_RELEASED'

                    WHEN r.status = 'RELEASED'

                    THEN 'HISTORY_RELEASED'

                    WHEN
                        r.status = 'DRAFT'

                        AND EXISTS (
                            SELECT 1

                            FROM recipes x

                            WHERE
                                x.machine_id = r.machine_id

                                AND x.stage_id = r.stage_id

                                AND UPPER(x.recipe_code) = UPPER(r.recipe_code)

                                AND x.version < r.version

                                AND x.status = 'RELEASED'
                        )

                    THEN 'DRAFT_REVISION'

                    ELSE r.status

                END AS version_usage_status

            FROM recipes r

            WHERE id = ?
            """,
            (
                source_recipe_id,
            )
        )

        source_recipe = cursor.fetchone()

        if not source_recipe:

            conn.close()

            return (

                False,

                "Source Recipe Not Found"

            )

        cursor.execute(
            """
            SELECT id

            FROM recipes

            WHERE UPPER(recipe_code) = ?
            """,
            (
                new_recipe_code.upper(),
            )
        )

        if cursor.fetchone():

            conn.close()

            return (

                False,

                "Recipe Code Already Exists"

            )

        cursor.execute(
            """
            INSERT INTO recipes
            (

                machine_id,

                stage_id,

                recipe_code,

                recipe_name,

                version,

                status,

                created_by

            )
            VALUES
            (?, ?, ?, ?, ?, ?, ?)
            """,
            (

                source_recipe["machine_id"],

                source_recipe["stage_id"],

                new_recipe_code,

                new_recipe_name,

                1,

                "DRAFT",

                username

            )
        )

        new_recipe_id = (
            cursor.lastrowid
        )

        cursor.execute(
            """
            SELECT *

            FROM recipe_parameter_values

            WHERE recipe_id = ?
            """,
            (
                source_recipe_id,
            )
        )

        parameter_rows = (
            cursor.fetchall()
        )

        for row in parameter_rows:

            cursor.execute(
                """
                INSERT INTO
                recipe_parameter_values
                (

                    recipe_id,

                    parameter_definition_id,

                    parameter_value,

                    is_modified

                )
                VALUES
                (?, ?, ?, ?)
                """,
                (

                    new_recipe_id,

                    row[
                        "parameter_definition_id"
                    ],

                    row[
                        "parameter_value"
                    ],

                    0

                )
            )

        cursor.execute(
            """
            SELECT *

            FROM recipe_phase_control

            WHERE recipe_id = ?
            """,
            (
                source_recipe_id,
            )
        )

        phase_rows = (
            cursor.fetchall()
        )

        for row in phase_rows:

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

                    new_recipe_id,

                    row["line_no"],

                    row["phase_control_id"],

                    row["stop_option"],

                    row["position_option"],

                    row["sequence_no"]

                )
            )

        conn.commit()

        conn.close()

        RecipeStatusHistoryManager.add_history(

            recipe_id=
            new_recipe_id,

            recipe_code=
            new_recipe_code,

            old_status=
            "",

            new_status=
            "DRAFT",

            changed_by=
            username,

            remarks=
            f"Copied From "
            f"{source_recipe['recipe_code']}"

        )

        return (

            True,

            new_recipe_id

        )

    @staticmethod
    def add_parameter(

        recipe_code,
        version,

        display_order,
        plc_array_index,

        parameter_group,
        category,

        parameter_name,
        recipe_parameter_description,

        plc_tag_name,

        parameter_value,

        data_type,

        unit,

        min_value,
        max_value

    ):

        conn = get_connection()
        cursor = conn.cursor()

        # ----------------------------------
        # Check duplicate parameter name
        # ----------------------------------

        cursor.execute("""
        SELECT id
        FROM recipe_parameters

        WHERE recipe_code = ?
        AND version = ?
        AND parameter_name = ?
        """, (

            recipe_code,
            version,
            parameter_name

        ))

        existing_parameter = cursor.fetchone()

        if existing_parameter:

            conn.close()

            raise ValueError(
                f"{parameter_name} already exists in {recipe_code}"
            )

        # ----------------------------------
        # Check duplicate PLC array index
        # ----------------------------------

        cursor.execute("""
        SELECT id
        FROM recipe_parameters

        WHERE recipe_code = ?
        AND version = ?
        AND plc_array_index = ?
        """, (

            recipe_code,
            version,
            plc_array_index

        ))

        existing_index = cursor.fetchone()

        if existing_index:

            conn.close()

            raise ValueError(
                f"PLC Array Index {plc_array_index} already used in {recipe_code}"
            )

        # ----------------------------------
        # Validate Min / Max Range
        # ----------------------------------

        if min_value is not None and parameter_value < min_value:

            conn.close()

            raise ValueError(
                f"{parameter_name} below minimum value ({min_value})"
            )

        if max_value is not None and parameter_value > max_value:

            conn.close()

            raise ValueError(
                f"{parameter_name} above maximum value ({max_value})"
            )

        # ----------------------------------
        # Insert Parameter
        # ----------------------------------

        cursor.execute("""
        INSERT INTO recipe_parameters (

            recipe_code,
            version,

            display_order,
            plc_array_index,

            parameter_group,
            category,

            parameter_name,
            recipe_parameter_description,

            plc_tag_name,

            parameter_value,

            data_type,

            unit,

            min_value,
            max_value

        )

        VALUES (

            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?

        )
        """, (

            recipe_code,
            version,

            display_order,
            plc_array_index,

            parameter_group,
            category,

            parameter_name,
            recipe_parameter_description,

            plc_tag_name,

            parameter_value,

            data_type,

            unit,

            min_value,
            max_value

        ))

        conn.commit()
        conn.close()

        print(
            f"Parameter Added : {parameter_name}"
        )

    @staticmethod
    def add_phase_control(

        recipe_code,
        version,

        phase_order,

        machine_side,

        phase_description,

        stop_flag

    ):

        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT id

        FROM recipe_phase_control

        WHERE recipe_code = ?
        AND version = ?
        AND phase_order = ?
        """, (

            recipe_code,
            version,
            phase_order

        ))

        if cursor.fetchone():

            conn.close()

            print(
                f"Warning : Phase Order {phase_order} already exists"
            )

            return False

        cursor.execute("""
        INSERT INTO recipe_phase_control (

            recipe_code,
            version,

            phase_order,

            machine_side,

            phase_description,

            stop_flag

        )

        VALUES (?, ?, ?, ?, ?, ?)
        """, (

            recipe_code,
            version,

            phase_order,

            machine_side,

            phase_description,

            stop_flag

        ))

        conn.commit()
        conn.close()

    @staticmethod
    def get_recipe(recipe_code):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM recipe_master
            WHERE recipe_code = ?
            """,
            (recipe_code,)
        )

        recipe = cursor.fetchone()

        conn.close()

        if recipe:

            return dict(recipe)

        return None
    
    @staticmethod
    def get_recipes_by_machine_stage(

        machine_id,

        stage_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT

                r.*,

                CASE
                    WHEN
                        r.status = 'RELEASED'

                        AND r.version = (
                            SELECT MAX(x.version)

                            FROM recipes x

                            WHERE
                                x.machine_id = r.machine_id

                                AND x.stage_id = r.stage_id

                                AND UPPER(x.recipe_code) = UPPER(r.recipe_code)

                                AND x.status = 'RELEASED'
                        )

                    THEN 1

                    ELSE 0

                END AS is_current_released,

                CASE
                    WHEN
                        r.status = 'RELEASED'

                        AND r.version = (
                            SELECT MAX(x.version)

                            FROM recipes x

                            WHERE
                                x.machine_id = r.machine_id

                                AND x.stage_id = r.stage_id

                                AND UPPER(x.recipe_code) = UPPER(r.recipe_code)

                                AND x.status = 'RELEASED'
                        )

                    THEN 'CURRENT_RELEASED'

                    WHEN r.status = 'RELEASED'

                    THEN 'HISTORY_RELEASED'

                    WHEN
                        r.status = 'DRAFT'

                        AND EXISTS (
                            SELECT 1

                            FROM recipes x

                            WHERE
                                x.machine_id = r.machine_id

                                AND x.stage_id = r.stage_id

                                AND UPPER(x.recipe_code) = UPPER(r.recipe_code)

                                AND x.version < r.version

                                AND x.status = 'RELEASED'
                        )

                    THEN 'DRAFT_REVISION'

                    ELSE r.status

                END AS version_usage_status

            FROM recipes r

            WHERE

                r.machine_id = ?

                AND r.stage_id = ?

            ORDER BY
                r.recipe_code,
                r.version DESC
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
    def get_recipe_by_id(

        recipe_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT

                r.*,

                (
                    SELECT x.id

                    FROM recipes x

                    WHERE
                        x.machine_id = r.machine_id

                        AND x.stage_id = r.stage_id

                        AND UPPER(x.recipe_code) = UPPER(r.recipe_code)

                        AND x.status = 'RELEASED'

                    ORDER BY
                        x.version DESC,
                        x.id DESC

                    LIMIT 1
                ) AS current_released_recipe_id,

                (
                    SELECT x.version

                    FROM recipes x

                    WHERE
                        x.machine_id = r.machine_id

                        AND x.stage_id = r.stage_id

                        AND UPPER(x.recipe_code) = UPPER(r.recipe_code)

                        AND x.status = 'RELEASED'

                    ORDER BY
                        x.version DESC,
                        x.id DESC

                    LIMIT 1
                ) AS current_released_version,

                CASE
                    WHEN
                        r.status = 'RELEASED'

                        AND r.version = (
                            SELECT MAX(x.version)

                            FROM recipes x

                            WHERE
                                x.machine_id = r.machine_id

                                AND x.stage_id = r.stage_id

                                AND UPPER(x.recipe_code) = UPPER(r.recipe_code)

                                AND x.status = 'RELEASED'
                        )

                    THEN 1

                    ELSE 0

                END AS is_current_released,

                CASE
                    WHEN
                        r.status = 'RELEASED'

                        AND r.version = (
                            SELECT MAX(x.version)

                            FROM recipes x

                            WHERE
                                x.machine_id = r.machine_id

                                AND x.stage_id = r.stage_id

                                AND UPPER(x.recipe_code) = UPPER(r.recipe_code)

                                AND x.status = 'RELEASED'
                        )

                    THEN 'CURRENT_RELEASED'

                    WHEN r.status = 'RELEASED'

                    THEN 'HISTORY_RELEASED'

                    WHEN
                        r.status = 'DRAFT'

                        AND EXISTS (
                            SELECT 1

                            FROM recipes x

                            WHERE
                                x.machine_id = r.machine_id

                                AND x.stage_id = r.stage_id

                                AND UPPER(x.recipe_code) = UPPER(r.recipe_code)

                                AND x.version < r.version

                                AND x.status = 'RELEASED'
                        )

                    THEN 'DRAFT_REVISION'

                    ELSE r.status

                END AS version_usage_status,

                m.machine_code,

                s.stage_type

            FROM recipes r

            LEFT JOIN tbm_machines m

            ON r.machine_id = m.id

            LEFT JOIN machine_stages s

            ON r.stage_id = s.id

            WHERE r.id = ?
            """,
            (
                recipe_id,
            )
        )

        row = cursor.fetchone()

        conn.close()

        if row:

            return dict(row)

        return None
    
    @staticmethod
    def assign_recipe_to_plc(
        recipe_code,
        plc_name
    ):

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT id

        FROM recipe_plc_mapping

        WHERE recipe_code = ?
        AND plc_name = ?
        """, (

            recipe_code,
            plc_name

        ))

        existing = cursor.fetchone()

        if existing:

            conn.close()

            print(
                f"Recipe {recipe_code} already assigned to {plc_name}"
            )

            return False

        cursor.execute("""
        INSERT INTO recipe_plc_mapping (

            recipe_code,
            plc_name

        )

        VALUES (?, ?)
        """, (

            recipe_code,
            plc_name

        ))

        conn.commit()
        conn.close()

        print(
            f"Recipe {recipe_code} assigned to {plc_name}"
        )

        return True
    
    @staticmethod
    def get_assigned_plcs(
        recipe_code
    ):

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT plc_name
        FROM recipe_plc_mapping

        WHERE recipe_code = ?
        """, (

            recipe_code,

        ))

        plcs = [row["plc_name"] for row in cursor.fetchall()]

        conn.close()

        return plcs
    
    @staticmethod
    def get_recipe_array(
        recipe_code,
        version=1
    ):

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT parameter_value

        FROM recipe_parameters

        WHERE recipe_code = ?
        AND version = ?

        ORDER BY plc_array_index
        """, (

            recipe_code,
            version

        ))

        recipe_array = [

            row["parameter_value"]

            for row in cursor.fetchall()

        ]

        conn.close()

        return recipe_array

    @staticmethod
    def get_recipe_dictionary(
        recipe_code,
        version=1
    ):

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT

            parameter_name,
            parameter_value

        FROM recipe_parameters

        WHERE recipe_code = ?
        AND version = ?

        ORDER BY display_order
        """, (

            recipe_code,
            version

        ))

        recipe = {}

        for row in cursor.fetchall():

            recipe[row["parameter_name"]] = row["parameter_value"]

        conn.close()

        return recipe
    
    @staticmethod
    def update_parameter(

        recipe_code,
        version,
        parameter_name,

        new_value,

        username,
        reason="Parameter Update"

    ):

        conn = get_connection()
        cursor = conn.cursor()

        # Get existing value

        cursor.execute("""
        SELECT parameter_value, min_value, max_value

        FROM recipe_parameters

        WHERE recipe_code = ?
        AND version = ?
        AND parameter_name = ?
        """, (

            recipe_code,
            version,
            parameter_name

        ))

        row = cursor.fetchone()

        if not row:

            conn.close()

            raise ValueError(
                f"{parameter_name} not found"
            )
        
        min_value = row["min_value"]
        max_value = row["max_value"]

        if min_value is not None:

            if float(new_value) < float(min_value):

                conn.close()

                raise ValueError(
                    f"Value below minimum ({min_value})"
                )

        if max_value is not None:

            if float(new_value) > float(max_value):

                conn.close()

                raise ValueError(
                    f"Value above maximum ({max_value})"
                )

        old_value = row["parameter_value"]
        
        if float(old_value) == float(new_value):

            conn.close()

            print(
                f"Warning : {parameter_name} already set to {new_value}"
            )

            return False

        # Update parameter

        cursor.execute("""
        UPDATE recipe_parameters

        SET parameter_value = ?

        WHERE recipe_code = ?
        AND version = ?
        AND parameter_name = ?
        """, (

            new_value,

            recipe_code,
            version,
            parameter_name

        ))

        # Update recipe master

        cursor.execute("""
        UPDATE recipe_master

        SET

            last_modified_by = ?,
            last_modified_at = CURRENT_TIMESTAMP

        WHERE recipe_code = ?
        """, (

            username,
            recipe_code

        ))

        conn.commit()

        AuditManager.log_parameter_change(

            username=username,

            recipe_code=recipe_code,

            recipe_version=version,

            parameter_name=parameter_name,

            old_value=str(old_value),

            new_value=str(new_value),

            reason=reason

        )

        conn.close()

        print(
            f"{parameter_name} Updated "
            f"{old_value} -> {new_value}"
        )
        
    @staticmethod
    def create_recipe_version(

        recipe_code,
        source_version,
        created_by

    ):

        conn = get_connection()
        cursor = conn.cursor()

        # --------------------------------
        # Find next version number
        # --------------------------------

        cursor.execute("""
        SELECT MAX(version) AS max_version

        FROM recipe_parameters

        WHERE recipe_code = ?
        """, (

            recipe_code,

        ))

        row = cursor.fetchone()

        max_version = row["max_version"]

        if max_version is None:

            conn.close()

            print(
                f"Warning : No versions found for {recipe_code}"
            )

            return False

        new_version = max_version + 1

        # --------------------------------
        # Copy Recipe Parameters
        # --------------------------------

        cursor.execute("""
        INSERT INTO recipe_parameters (

            recipe_code,
            version,

            display_order,
            plc_array_index,

            category,
            parameter_group,

            parameter_name,
            recipe_parameter_description,

            plc_tag_name,

            parameter_value,

            data_type,

            unit,

            min_value,
            max_value

        )

        SELECT

            recipe_code,
            ?,

            display_order,
            plc_array_index,

            category,
            parameter_group,

            parameter_name,
            recipe_parameter_description,

            plc_tag_name,

            parameter_value,

            data_type,

            unit,

            min_value,
            max_value

        FROM recipe_parameters

        WHERE recipe_code = ?
        AND version = ?
        """, (

            new_version,

            recipe_code,
            source_version

        ))

        # --------------------------------
        # Copy Phase Control
        # --------------------------------

        cursor.execute("""
        INSERT INTO recipe_phase_control (

            recipe_code,
            version,

            phase_order,

            machine_side,

            phase_description,

            stop_flag

        )

        SELECT

            recipe_code,
            ?,

            phase_order,

            machine_side,

            phase_description,

            stop_flag

        FROM recipe_phase_control

        WHERE recipe_code = ?
        AND version = ?
        """, (

            new_version,

            recipe_code,
            source_version

        ))

        # --------------------------------
        # Update Recipe Master
        # --------------------------------

        cursor.execute("""
        UPDATE recipe_master

        SET

            current_version = ?,
            last_modified_by = ?,
            last_modified_at = CURRENT_TIMESTAMP

        WHERE recipe_code = ?
        """, (

            new_version,
            created_by,
            recipe_code

        ))

        conn.commit()
        conn.close()

        # --------------------------------
        # Audit Log
        # --------------------------------

        AuditManager.log_event(

            username=created_by,

            role="EDITOR",

            action="RECIPE_VERSION_CREATED",

            change_source="DATABASE",

            recipe_code=recipe_code,

            recipe_version=new_version,

            old_value=str(source_version),

            new_value=str(new_version),

            reason="Recipe Version Created"

        )

        RecipeManager.create_version_record(

            recipe_code=recipe_code,

            version=new_version,

            created_by=created_by

        )

        print(
            f"{recipe_code} Version {new_version} Created"
        )

        return new_version    
    
    @staticmethod
    def update_recipe_status(

        recipe_code,
        status,
        username

    ):

        allowed_statuses = [

            "DRAFT",
            "UNDER_REVIEW",
            "APPROVED",
            "RELEASED",
            "OBSOLETE"

        ]

        if status not in allowed_statuses:

            print(
                f"Warning : Invalid Status : {status}"
            )

            return False

        conn = get_connection()
        cursor = conn.cursor()

        # Current status

        cursor.execute("""
        SELECT recipe_status

        FROM recipe_master

        WHERE recipe_code = ?
        """, (

            recipe_code,

        ))

        row = cursor.fetchone()

        if not row:

            conn.close()

            print(
                f"Warning : Recipe Not Found : {recipe_code}"
            )

            return False

        old_status = row["recipe_status"]

        # Update status

        cursor.execute("""
        UPDATE recipe_master

        SET

            recipe_status = ?,

            last_modified_by = ?,

            last_modified_at = CURRENT_TIMESTAMP

        WHERE recipe_code = ?
        """, (

            status,

            username,

            recipe_code

        ))

        conn.commit()
        conn.close()

        # Audit Log

        AuditManager.log_event(

            username=username,

            role="EDITOR",

            action="RECIPE_STATUS_CHANGED",

            change_source="DATABASE",

            recipe_code=recipe_code,

            old_value=old_status,

            new_value=status,

            reason="Recipe Status Change"

        )

        print(
            f"{recipe_code} : {old_status} -> {status}"
        )

    @staticmethod
    def get_parameter(
        recipe_code,
        parameter_name
    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM recipe_parameters

            WHERE recipe_code = ?
            AND parameter_name = ?

            LIMIT 1
            """,
            (
                recipe_code,
                parameter_name
            )
        )

        row = cursor.fetchone()

        conn.close()

        if row:

            return dict(row)

        return None
    
    @staticmethod
    def update_parameter_metadata(

        recipe_code,
        version,

        parameter_name,

        min_value,
        max_value,

        unit,

        username

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE recipe_parameters

            SET

                min_value = ?,
                max_value = ?,
                unit = ?

            WHERE recipe_code = ?
            AND version = ?
            AND parameter_name = ?
            """,
            (
                min_value,
                max_value,
                unit,
                recipe_code,
                version,
                parameter_name
            )
        )

        cursor.execute(
            """
            UPDATE recipe_master

            SET

                last_modified_by = ?,
                last_modified_at = CURRENT_TIMESTAMP

            WHERE recipe_code = ?
            """,
            (
                username,
                recipe_code
            )
        )

        conn.commit()

        conn.close()

    @staticmethod
    def get_recipe_parameters(
        recipe_code,
        version
    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM recipe_parameters

            WHERE recipe_code = ?
            AND version = ?

            ORDER BY display_order
            """,
            (
                recipe_code,
                version
            )
        )

        rows = cursor.fetchall()

        conn.close()

        return [
            dict(row)
            for row in rows
        ]
    
    @staticmethod
    def get_recipe_versions(
        recipe_code
    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT DISTINCT version

            FROM recipe_parameters

            WHERE recipe_code = ?

            ORDER BY version
            """,
            (
                recipe_code,
            )
        )

        rows = cursor.fetchall()

        conn.close()

        return [
            row["version"]
            for row in rows
        ]
    
    @staticmethod
    def compare_versions(
        recipe_code,
        version_a,
        version_b
    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT

                a.parameter_name,

                a.parameter_value AS value_a,

                b.parameter_value AS value_b

            FROM recipe_parameters a

            INNER JOIN recipe_parameters b

                ON a.recipe_code = b.recipe_code

                AND a.parameter_name = b.parameter_name

            WHERE

                a.recipe_code = ?

                AND a.version = ?

                AND b.version = ?

            ORDER BY a.display_order
            """,
            (
                recipe_code,
                version_a,
                version_b
            )
        )

        rows = cursor.fetchall()

        conn.close()

        result = []

        for row in rows:

            item = dict(row)

            item["changed"] = (
                item["value_a"] != item["value_b"]
            )

            result.append(
                item
            )

        return result
    
    @staticmethod
    def create_version_record(

        recipe_code,

        version,

        created_by

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO recipe_versions
            (
                recipe_code,
                version,
                created_by
            )
            VALUES
            (
                ?, ?, ?
            )
            """,
            (
                recipe_code,
                version,
                created_by
            )
        )

        conn.commit()

        conn.close()

    @staticmethod
    def get_version_details(

        recipe_code,

        version

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM recipe_versions

            WHERE recipe_code = ?
            AND version = ?
            """,
            (
                recipe_code,
                version
            )
        )

        row = cursor.fetchone()

        conn.close()

        if row:

            return dict(row)

        return None
    
    @staticmethod
    def add_engineering_unit(

        unit_code,

        description

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO engineering_units
            (
                unit_code,
                description
            )
            VALUES
            (
                ?, ?
            )
            """,
            (
                unit_code,
                description
            )
        )

        conn.commit()

        conn.close()

    @staticmethod
    def get_active_engineering_units():

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM engineering_units

            WHERE is_active = 1

            ORDER BY unit_code
            """
        )

        rows = cursor.fetchall()

        conn.close()

        return [
            dict(row)
            for row in rows
        ]
    
    @staticmethod
    def get_all_engineering_units():

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM engineering_units

            ORDER BY unit_code
            """
        )

        rows = cursor.fetchall()

        conn.close()

        return [
            dict(row)
            for row in rows
        ]
    
    @staticmethod
    def disable_engineering_unit(
        unit_id
    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE engineering_units

            SET is_active = 0

            WHERE id = ?
            """,
            (unit_id,)
        )

        conn.commit()

        conn.close()

    @staticmethod
    def update_engineering_unit(

        unit_id,

        description

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE engineering_units

            SET description = ?

            WHERE id = ?
            """,
            (
                description,
                unit_id
            )
        )

        conn.commit()

        conn.close()

    @staticmethod
    def get_engineering_unit(
        unit_id
    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM engineering_units

            WHERE id = ?
            """,
            (unit_id,)
        )

        row = cursor.fetchone()

        conn.close()

        if row:

            return dict(row)

        return None
    
    @staticmethod
    def enable_engineering_unit(
        unit_id
    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE engineering_units

            SET is_active = 1

            WHERE id = ?
            """,
            (unit_id,)
        )

        conn.commit()

        conn.close()
