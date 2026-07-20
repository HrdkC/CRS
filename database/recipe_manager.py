# database/recipe_manager.py

import uuid

from config.settings import ALLOW_LEGACY_RECIPE_WRITES
from database.database import get_connection, transaction
from database.audit_manager import AuditManager


class RecipeManager:

    @staticmethod
    def _require_legacy_write_enabled(operation):
        if not ALLOW_LEGACY_RECIPE_WRITES:
            raise RuntimeError(
                f"Legacy recipe mutation blocked: {operation}. "
                "Use the canonical recipe-ID workflow."
            )


    @staticmethod
    def create_recipe(
        machine_id,
        stage_id,
        recipe_code,
        recipe_name,
        created_by
    ):
        """Create the recipe, its values, phase rows, status history and audit atomically."""
        from database.phase_control_default_manager import PhaseControlDefaultManager

        recipe_code = (recipe_code or "").strip().upper()
        recipe_name = (recipe_name or "").strip()
        if not recipe_code:
            raise ValueError("Recipe code is required.")
        if not recipe_name:
            raise ValueError("Recipe name is required.")

        # Phase-master seeding is a controlled configuration action and must
        # finish before the business-data transaction begins.
        stage_conn = get_connection()
        try:
            stage = stage_conn.execute(
                """
                SELECT s.stage_type, m.machine_code
                FROM machine_stages s
                JOIN tbm_machines m ON m.id = s.machine_id
                WHERE s.id=? AND s.machine_id=?
                """,
                (int(stage_id), int(machine_id)),
            ).fetchone()
        finally:
            stage_conn.close()
        if not stage:
            raise ValueError("Machine/stage not found.")

        stage_type = stage["stage_type"]
        PhaseControlDefaultManager.initialize_for_stage(stage_id, stage_type)
        correlation_id = str(uuid.uuid4())

        with transaction(immediate=True) as conn:
            cursor = conn.cursor()
            duplicate = cursor.execute(
                """
                SELECT id FROM recipes
                WHERE machine_id=? AND stage_id=? AND UPPER(recipe_code)=?
                LIMIT 1
                """,
                (int(machine_id), int(stage_id), recipe_code),
            ).fetchone()
            if duplicate:
                raise ValueError("Recipe code already exists for this machine/stage.")

            parameter_count = cursor.execute(
                """
                SELECT COUNT(*)
                FROM parameter_definitions
                WHERE machine_id=? AND stage_id=? AND COALESCE(used, 1)=1
                """,
                (int(machine_id), int(stage_id)),
            ).fetchone()[0]
            if int(parameter_count or 0) <= 0:
                raise ValueError(
                    "Parameter master is not configured for this machine/stage. "
                    "Build/import parameter definitions before creating recipe."
                )

            cursor.execute(
                """
                INSERT INTO recipes
                (machine_id, stage_id, recipe_code, recipe_name, created_by)
                VALUES (?, ?, ?, ?, ?)
                """,
                (machine_id, stage_id, recipe_code, recipe_name, created_by),
            )
            recipe_id = int(cursor.lastrowid)

            cursor.execute(
                """
                INSERT INTO recipe_parameter_values
                (recipe_id, parameter_definition_id, parameter_value, is_modified)
                SELECT ?, id, COALESCE(default_value, 0), 0
                FROM parameter_definitions
                WHERE machine_id=? AND stage_id=? AND COALESCE(used, 1)=1
                ORDER BY tag_index
                """,
                (recipe_id, machine_id, stage_id),
            )

            stage_key = str(stage_type or "").strip().upper().replace(" ", "_")
            is_second_stage = stage_key in {"SECOND_STAGE", "SECONDSTAGE", "SS"}
            group_codes = ("CAP_STRIP_SIDE", "BT_SIDE") if is_second_stage else ("MAIN",)
            slots = 6 if is_second_stage else 12

            for group_code in group_codes:
                group = cursor.execute(
                    """
                    SELECT phase_group_name
                    FROM phase_control_group_master
                    WHERE machine_stage_id=?
                      AND UPPER(COALESCE(phase_group_code, 'MAIN'))=?
                      AND COALESCE(active, 1)=1
                    LIMIT 1
                    """,
                    (stage_id, group_code),
                ).fetchone()
                group_name = (
                    group["phase_group_name"]
                    if group
                    else group_code.replace("_", " ").title()
                )
                empty_phase = cursor.execute(
                    """
                    SELECT id FROM phase_control_master
                    WHERE machine_stage_id=?
                      AND UPPER(COALESCE(phase_group_code, 'MAIN'))=?
                      AND UPPER(COALESCE(phase_control_key, phase_control_name))='EMPTY PHASE'
                      AND COALESCE(active, 1)=1
                    LIMIT 1
                    """,
                    (stage_id, group_code),
                ).fetchone()
                if not empty_phase:
                    raise ValueError(
                        f"Empty Phase master is missing for {stage_type}/{group_code}."
                    )
                for line_no in range(1, slots + 1):
                    cursor.execute(
                        """
                        INSERT INTO recipe_phase_control
                        (recipe_id, phase_group_code, phase_group_name, line_no,
                         phase_control_id, stop_option, position_option, sequence_no, used)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                        """,
                        (
                            recipe_id,
                            group_code,
                            group_name,
                            line_no,
                            int(empty_phase["id"]),
                            None if is_second_stage else "No",
                            None if is_second_stage else "No",
                            line_no,
                        ),
                    )

            cursor.execute(
                """
                INSERT INTO recipe_status_history
                (recipe_id, recipe_code, old_status, new_status, changed_by, remarks)
                VALUES (?, ?, '', 'DRAFT', ?, ?)
                """,
                (recipe_id, recipe_code, created_by, "Canonical recipe created"),
            )
            user_row = cursor.execute(
                "SELECT role FROM users WHERE LOWER(username)=LOWER(?) LIMIT 1",
                (created_by,),
            ).fetchone()
            AuditManager.log_event(
                username=created_by,
                role=(user_row["role"] if user_row else "UNKNOWN"),
                action="RECIPE_CREATED",
                change_source="CANONICAL_RECIPE_CREATE",
                recipe_code=recipe_code,
                recipe_version=1,
                record_id=recipe_id,
                new_value=f"{stage['machine_code']}/{stage_type}/{recipe_name}",
                reason="Canonical recipe created from active machine/stage templates",
                correlation_id=correlation_id,
                _connection=conn,
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
        """Copy a canonical recipe as one atomic transaction.

        P15 Second Stage copies deliberately retain only CAP_STRIP_SIDE and
        BT_SIDE phase selections. Stop/position are fixed non-recipe data and
        are stored as NULL in the new recipe.
        """
        new_recipe_code = (new_recipe_code or "").strip().upper()
        new_recipe_name = (new_recipe_name or "").strip()
        if not new_recipe_code or not new_recipe_name:
            return False, "Recipe code and name are required"

        correlation_id = str(uuid.uuid4())
        try:
            with transaction(immediate=True) as conn:
                cursor = conn.cursor()
                source_recipe = cursor.execute(
                    """
                    SELECT r.*, s.stage_type, m.machine_code
                    FROM recipes r
                    JOIN machine_stages s ON s.id = r.stage_id
                    JOIN tbm_machines m ON m.id = r.machine_id
                    WHERE r.id = ?
                    """,
                    (int(source_recipe_id),),
                ).fetchone()
                if not source_recipe:
                    raise ValueError("Source Recipe Not Found")

                duplicate = cursor.execute(
                    """
                    SELECT id FROM recipes
                    WHERE machine_id=? AND stage_id=? AND UPPER(recipe_code)=?
                    LIMIT 1
                    """,
                    (
                        source_recipe["machine_id"],
                        source_recipe["stage_id"],
                        new_recipe_code,
                    ),
                ).fetchone()
                if duplicate:
                    raise ValueError("Recipe Code Already Exists for this machine/stage")

                cursor.execute(
                    """
                    INSERT INTO recipes
                    (machine_id, stage_id, recipe_code, recipe_name, version, status, created_by)
                    VALUES (?, ?, ?, ?, 1, 'DRAFT', ?)
                    """,
                    (
                        source_recipe["machine_id"],
                        source_recipe["stage_id"],
                        new_recipe_code,
                        new_recipe_name,
                        username,
                    ),
                )
                new_recipe_id = int(cursor.lastrowid)

                cursor.execute(
                    """
                    INSERT INTO recipe_parameter_values
                    (recipe_id, parameter_definition_id, parameter_value, is_modified)
                    SELECT ?, parameter_definition_id, parameter_value, 0
                    FROM recipe_parameter_values
                    WHERE recipe_id=?
                    """,
                    (new_recipe_id, int(source_recipe_id)),
                )

                phase_columns = {
                    row[1]
                    for row in cursor.execute("PRAGMA table_info(recipe_phase_control)")
                }
                has_group_columns = {
                    "phase_group_code", "phase_group_name", "used"
                }.issubset(phase_columns)
                stage_key = str(source_recipe["stage_type"] or "").upper().replace(" ", "_")
                is_second_stage = stage_key in {"SECOND_STAGE", "SECONDSTAGE", "SS"}

                if has_group_columns:
                    group_filter = ""
                    params = [new_recipe_id, int(source_recipe_id)]
                    if is_second_stage:
                        group_filter = (
                            " AND UPPER(COALESCE(phase_group_code, '')) "
                            "IN ('CAP_STRIP_SIDE', 'BT_SIDE')"
                        )
                    cursor.execute(
                        f"""
                        INSERT INTO recipe_phase_control
                        (recipe_id, phase_group_code, phase_group_name, line_no,
                         phase_control_id, stop_option, position_option,
                         sequence_no, used)
                        SELECT ?, phase_group_code, phase_group_name, line_no,
                               phase_control_id,
                               {"NULL" if is_second_stage else "stop_option"},
                               {"NULL" if is_second_stage else "position_option"},
                               sequence_no, COALESCE(used, 1)
                        FROM recipe_phase_control
                        WHERE recipe_id=? {group_filter}
                        ORDER BY phase_group_code, line_no
                        """,
                        params,
                    )
                else:
                    if is_second_stage:
                        raise ValueError(
                            "Second Stage recipe copy requires migrated phase-group columns."
                        )
                    cursor.execute(
                        """
                        INSERT INTO recipe_phase_control
                        (recipe_id, line_no, phase_control_id, stop_option,
                         position_option, sequence_no)
                        SELECT ?, line_no, phase_control_id, stop_option,
                               position_option, sequence_no
                        FROM recipe_phase_control
                        WHERE recipe_id=?
                        ORDER BY line_no
                        """,
                        (new_recipe_id, int(source_recipe_id)),
                    )

                cursor.execute(
                    """
                    INSERT INTO recipe_status_history
                    (recipe_id, recipe_code, old_status, new_status, changed_by, remarks)
                    VALUES (?, ?, '', 'DRAFT', ?, ?)
                    """,
                    (
                        new_recipe_id,
                        new_recipe_code,
                        username,
                        f"Copied from {source_recipe['recipe_code']}",
                    ),
                )
                user_row = cursor.execute(
                    "SELECT role FROM users WHERE LOWER(username)=LOWER(?) LIMIT 1",
                    (username,),
                ).fetchone()
                AuditManager.log_event(
                    username=username,
                    role=(user_row["role"] if user_row else "UNKNOWN"),
                    action="RECIPE_COPIED",
                    change_source="CANONICAL_RECIPE_COPY",
                    recipe_code=new_recipe_code,
                    recipe_version=1,
                    record_id=new_recipe_id,
                    old_value=f"source_recipe_id={source_recipe_id}",
                    new_value=(
                        f"{source_recipe['machine_code']}/"
                        f"{source_recipe['stage_type']}/{new_recipe_name}"
                    ),
                    reason=f"Copied from {source_recipe['recipe_code']}",
                    correlation_id=correlation_id,
                    _connection=conn,
                )
            return True, new_recipe_id
        except ValueError as exc:
            return False, str(exc)

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

        RecipeManager._require_legacy_write_enabled("add_parameter")

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

        RecipeManager._require_legacy_write_enabled("add_phase_control")

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

        RecipeManager._require_legacy_write_enabled("assign_recipe_to_plc")

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

        RecipeManager._require_legacy_write_enabled("update_parameter")

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

        RecipeManager._require_legacy_write_enabled("create_recipe_version")

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

        RecipeManager._require_legacy_write_enabled("update_recipe_status")

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

        RecipeManager._require_legacy_write_enabled("update_parameter_metadata")

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

        RecipeManager._require_legacy_write_enabled("create_version_record")

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
