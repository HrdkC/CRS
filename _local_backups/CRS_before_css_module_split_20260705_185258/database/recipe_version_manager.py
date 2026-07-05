from database.database import (
    get_connection
)


class RecipeVersionManager:

    @staticmethod
    def create_version(

        recipe_id,

        version_comment,

        created_by

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT

                recipe_code

            FROM recipes

            WHERE id = ?
            """,
            (
                recipe_id,
            )
        )

        recipe = cursor.fetchone()

        if not recipe:

            conn.close()

            raise Exception(
                "Recipe Not Found"
            )

        recipe_code = recipe[
            "recipe_code"
        ]

        cursor.execute(
            """
            SELECT

                MAX(version)

            FROM recipe_versions

            WHERE recipe_id = ?
            """,
            (
                recipe_id,
            )
        )

        row = cursor.fetchone()

        current_version = row[0]

        if current_version is None:

            current_version = 0

        next_version = (

            current_version + 1

        )

        cursor.execute(
            """
            INSERT INTO
            recipe_versions
            (

                recipe_id,

                recipe_code,

                version,

                version_comment,

                created_by

            )
            VALUES
            (?, ?, ?, ?, ?)
            """,
            (
                recipe_id,

                recipe_code,

                next_version,

                version_comment,

                created_by
            )
        )

        recipe_version_id = (
            cursor.lastrowid
        )

        cursor.execute(
            """
            SELECT

                parameter_definition_id,

                parameter_value

            FROM
            recipe_parameter_values

            WHERE recipe_id = ?
            """,
            (
                recipe_id,
            )
        )

        values = cursor.fetchall()

        for value in values:

            cursor.execute(
                """
                INSERT INTO
                recipe_version_values
                (

                    recipe_version_id,

                    parameter_definition_id,

                    parameter_value

                )
                VALUES
                (?, ?, ?)
                """,
                (
                    recipe_version_id,

                    value[
                        "parameter_definition_id"
                    ],

                    value[
                        "parameter_value"
                    ]
                )
            )

        cursor.execute(
            """
            UPDATE recipes

            SET

                version = ?,

                updated_at =
                CURRENT_TIMESTAMP

            WHERE id = ?
            """,
            (
                next_version,
                recipe_id
            )
        )

        conn.commit()

        conn.close()

        return recipe_version_id

    @staticmethod
    def get_versions(

        recipe_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM recipe_versions

            WHERE recipe_id = ?

            ORDER BY
                version DESC
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
    def restore_version(

        recipe_version_id,

        restored_by

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM recipe_versions

            WHERE id = ?
            """,
            (
                recipe_version_id,
            )
        )

        version = cursor.fetchone()

        if not version:

            conn.close()

            raise Exception(
                "Version Not Found"
            )

        recipe_id = version[
            "recipe_id"
        ]

        cursor.execute(
            """
            SELECT *

            FROM recipe_version_values

            WHERE
                recipe_version_id = ?
            """,
            (
                recipe_version_id,
            )
        )

        snapshot_values = (
            cursor.fetchall()
        )

        for row in snapshot_values:

            cursor.execute(
                """
                UPDATE
                recipe_parameter_values

                SET

                    parameter_value = ?,

                    is_modified = 1,

                    updated_at =
                    CURRENT_TIMESTAMP

                WHERE

                    recipe_id = ?

                    AND

                    parameter_definition_id = ?
                """,
                (
                    row[
                        "parameter_value"
                    ],

                    recipe_id,

                    row[
                        "parameter_definition_id"
                    ]
                )
            )

        conn.commit()

        conn.close()

    @staticmethod
    def get_version_by_id(

        recipe_version_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM recipe_versions

            WHERE id = ?
            """,
            (
                recipe_version_id,
            )
        )

        row = cursor.fetchone()

        conn.close()

        if row:

            return dict(row)

        return None

    @staticmethod
    def get_recipe_record_versions(

        recipe_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM recipes

            WHERE id = ?
            """,
            (
                recipe_id,
            )
        )

        recipe = cursor.fetchone()

        if not recipe:

            conn.close()

            return []

        cursor.execute(
            """
            SELECT

                r.*,

                (
                    SELECT COUNT(*)

                    FROM recipe_parameter_values rpv

                    WHERE rpv.recipe_id = r.id
                ) AS parameter_count

                ,

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

                END AS is_current_released

                ,

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

                    WHEN
                        r.status = 'REVIEW'

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

                    THEN 'REVISION_REVIEW'

                    ELSE r.status

                END AS version_usage_status

            FROM recipes r

            WHERE

                r.machine_id = ?

                AND r.stage_id = ?

                AND UPPER(r.recipe_code) = UPPER(?)

            ORDER BY
                r.version DESC,
                r.id DESC
            """,
            (
                recipe["machine_id"],
                recipe["stage_id"],
                recipe["recipe_code"]
            )
        )

        rows = cursor.fetchall()

        conn.close()

        return [

            dict(row)

            for row in rows

        ]

    @staticmethod
    def get_current_released_version(

        recipe_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM recipes

            WHERE id = ?
            """,
            (
                recipe_id,
            )
        )

        recipe = cursor.fetchone()

        if not recipe:

            conn.close()

            return None

        cursor.execute(
            """
            SELECT *

            FROM recipes

            WHERE

                machine_id = ?

                AND stage_id = ?

                AND UPPER(recipe_code) = UPPER(?)

                AND status = 'RELEASED'

            ORDER BY
                version DESC,
                id DESC

            LIMIT 1
            """,
            (
                recipe["machine_id"],
                recipe["stage_id"],
                recipe["recipe_code"]
            )
        )

        current = cursor.fetchone()

        conn.close()

        if current:

            return dict(current)

        return None

    @staticmethod
    def get_previous_released_version(

        recipe_id

    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM recipes

            WHERE id = ?
            """,
            (
                recipe_id,
            )
        )

        recipe = cursor.fetchone()

        if not recipe:

            conn.close()

            return None

        cursor.execute(
            """
            SELECT *

            FROM recipes

            WHERE

                machine_id = ?

                AND stage_id = ?

                AND UPPER(recipe_code) = UPPER(?)

                AND version < ?

                AND status = 'RELEASED'

            ORDER BY
                version DESC,
                id DESC

            LIMIT 1
            """,
            (
                recipe["machine_id"],
                recipe["stage_id"],
                recipe["recipe_code"],
                recipe["version"]
            )
        )

        previous = cursor.fetchone()

        conn.close()

        if previous:

            return dict(previous)

        return None

    @staticmethod
    def create_production_revision(

        recipe_id,

        version_comment,

        created_by,

        user_role="PRODUCTION"

    ):

        from database.audit_manager import (
            AuditManager
        )

        from database.recipe_status_history_manager import (
            RecipeStatusHistoryManager
        )

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM recipes

            WHERE id = ?
            """,
            (
                recipe_id,
            )
        )

        source_recipe = cursor.fetchone()

        if not source_recipe:

            conn.close()

            return (

                False,

                "Recipe Not Found",

                None

            )

        source_recipe = dict(
            source_recipe
        )

        if source_recipe["status"] != "RELEASED":

            conn.close()

            return (

                False,

                "Only RELEASED recipes can use production fast edit.",

                recipe_id

            )

        cursor.execute(
            """
            SELECT *

            FROM recipes

            WHERE

                machine_id = ?

                AND stage_id = ?

                AND UPPER(recipe_code) = UPPER(?)

                AND status = 'RELEASED'

            ORDER BY
                version DESC,
                id DESC

            LIMIT 1
            """,
            (
                source_recipe["machine_id"],
                source_recipe["stage_id"],
                source_recipe["recipe_code"]
            )
        )

        current_released = cursor.fetchone()

        if (
            current_released
            and
            current_released["id"] != source_recipe["id"]
        ):

            current_released = dict(
                current_released
            )

            conn.close()

            return (

                False,

                f"Only current released version can be edited. "
                f"Open V{current_released['version']} instead.",

                current_released["id"]

            )

        cursor.execute(
            """
            SELECT *

            FROM recipes

            WHERE

                machine_id = ?

                AND stage_id = ?

                AND UPPER(recipe_code) = UPPER(?)

                AND status != 'RELEASED'

            ORDER BY
                version DESC,
                id DESC

            LIMIT 1
            """,
            (
                source_recipe["machine_id"],
                source_recipe["stage_id"],
                source_recipe["recipe_code"]
            )
        )

        open_revision = cursor.fetchone()

        if open_revision:

            open_revision = dict(
                open_revision
            )

            conn.close()

            return (

                True,

                f"Editable revision already exists: "
                f"V{open_revision['version']}",

                open_revision["id"]

            )

        cursor.execute(
            """
            SELECT MAX(version) AS max_version

            FROM recipes

            WHERE

                machine_id = ?

                AND stage_id = ?

                AND UPPER(recipe_code) = UPPER(?)
            """,
            (
                source_recipe["machine_id"],
                source_recipe["stage_id"],
                source_recipe["recipe_code"]
            )
        )

        row = cursor.fetchone()

        next_version = (

            row["max_version"]
            or
            source_recipe["version"]

        ) + 1

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
                source_recipe["recipe_code"],
                source_recipe["recipe_name"],
                next_version,
                "DRAFT",
                created_by
            )
        )

        new_recipe_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO recipe_parameter_values
            (
                recipe_id,
                parameter_definition_id,
                parameter_value,
                is_modified
            )
            SELECT
                ?,
                parameter_definition_id,
                parameter_value,
                0
            FROM recipe_parameter_values
            WHERE recipe_id = ?
            """,
            (
                new_recipe_id,
                recipe_id
            )
        )

        cursor.execute(
            """
            INSERT INTO recipe_phase_control
            (
                recipe_id,
                line_no,
                phase_control_id,
                stop_option,
                position_option,
                sequence_no
            )
            SELECT
                ?,
                line_no,
                phase_control_id,
                stop_option,
                position_option,
                sequence_no
            FROM recipe_phase_control
            WHERE recipe_id = ?
            """,
            (
                new_recipe_id,
                recipe_id
            )
        )

        cursor.execute(
            """
            INSERT INTO recipe_versions
            (
                recipe_id,
                recipe_code,
                version,
                version_comment,
                created_by
            )
            VALUES
            (?, ?, ?, ?, ?)
            """,
            (
                new_recipe_id,
                source_recipe["recipe_code"],
                next_version,
                version_comment,
                created_by
            )
        )

        conn.commit()

        conn.close()

        RecipeStatusHistoryManager.add_history(

            recipe_id=new_recipe_id,

            recipe_code=source_recipe[
                "recipe_code"
            ],

            old_status="",

            new_status="DRAFT",

            changed_by=created_by,

            remarks=(
                f"Production revision created from "
                f"V{source_recipe['version']}. "
                f"{version_comment}"
            ).strip()

        )

        AuditManager.log_event(

            username=created_by,

            role=user_role,

            action="PRODUCTION_REVISION_CREATED",

            change_source="DATABASE",

            recipe_code=source_recipe[
                "recipe_code"
            ],

            recipe_version=next_version,

            record_id=new_recipe_id,

            old_value=(
                f"V{source_recipe['version']} "
                f"RELEASED"
            ),

            new_value=(
                f"V{next_version} "
                f"DRAFT"
            ),

            reason=version_comment

        )

        return (

            True,

            f"Production revision V{next_version} created.",

            new_recipe_id

        )

    @staticmethod
    def release_production_revision(

        recipe_id,

        released_by,

        remarks,

        user_role="PRODUCTION"

    ):

        from database.audit_manager import (
            AuditManager
        )

        from database.recipe_status_history_manager import (
            RecipeStatusHistoryManager
        )

        from database.recipe_validation_manager import (
            RecipeValidationManager
        )

        if not remarks:

            return (

                False,

                "Production release remarks required."

            )

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *

            FROM recipes

            WHERE id = ?
            """,
            (
                recipe_id,
            )
        )

        recipe = cursor.fetchone()

        if not recipe:

            conn.close()

            return (

                False,

                "Recipe Not Found"

            )

        recipe = dict(
            recipe
        )

        if recipe["status"] != "DRAFT":

            conn.close()

            return (

                False,

                "Only DRAFT production revisions can be released directly."

            )

        cursor.execute(
            """
            SELECT *

            FROM recipes

            WHERE

                machine_id = ?

                AND stage_id = ?

                AND UPPER(recipe_code) = UPPER(?)

                AND version < ?

                AND status = 'RELEASED'

            ORDER BY
                version DESC,
                id DESC

            LIMIT 1
            """,
            (
                recipe["machine_id"],
                recipe["stage_id"],
                recipe["recipe_code"],
                recipe["version"]
            )
        )

        previous_released = cursor.fetchone()

        cursor.execute(
            """
            SELECT *

            FROM recipes

            WHERE

                machine_id = ?

                AND stage_id = ?

                AND UPPER(recipe_code) = UPPER(?)

                AND status = 'RELEASED'

            ORDER BY
                version DESC,
                id DESC

            LIMIT 1
            """,
            (
                recipe["machine_id"],
                recipe["stage_id"],
                recipe["recipe_code"]
            )
        )

        current_released = cursor.fetchone()

        conn.close()

        if not previous_released:

            return (

                False,

                "Direct production release is allowed only for revisions "
                "created from an existing RELEASED recipe."

            )

        if (
            current_released
            and
            current_released["version"] > recipe["version"]
        ):

            return (

                False,

                f"Cannot release V{recipe['version']} because "
                f"V{current_released['version']} is already current."

            )

        validation = (
            RecipeValidationManager
            .validate_recipe(

                recipe_id,

                require_released=False

            )
        )

        if not validation["valid"]:

            return (

                False,

                "Validation Failed : "
                + "; ".join(
                    validation["errors"][:5]
                )

            )

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE recipes

            SET

                status = 'RELEASED',

                updated_at = CURRENT_TIMESTAMP

            WHERE id = ?
            """,
            (
                recipe_id,
            )
        )

        conn.commit()

        conn.close()

        RecipeStatusHistoryManager.add_history(

            recipe_id=recipe_id,

            recipe_code=recipe[
                "recipe_code"
            ],

            old_status="DRAFT",

            new_status="RELEASED",

            changed_by=released_by,

            remarks=(
                "Production fast release. "
                + remarks
            ).strip()

        )

        AuditManager.log_event(

            username=released_by,

            role=user_role,

            action="PRODUCTION_REVISION_RELEASED",

            change_source="DATABASE",

            recipe_code=recipe[
                "recipe_code"
            ],

            recipe_version=recipe[
                "version"
            ],

            record_id=recipe_id,

            old_value="DRAFT",

            new_value="RELEASED",

            reason=remarks

        )

        return (

            True,

            "Production revision released."

        )
