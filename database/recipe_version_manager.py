import uuid

from database.database import (
    get_connection, transaction
)
from database.audit_manager import AuditManager
from database.recipe_parameter_audit_manager import RecipeParameterAuditManager


class RecipeVersionManager:

    @staticmethod
    def create_version(
        recipe_id,
        version_comment,
        created_by,
        user_role="PRODUCTION",
    ):
        """Create a point-in-time parameter snapshot atomically.

        Snapshot creation does not change the recipe lifecycle or production
        values.  It records one correlated general audit event.
        """
        comment = str(version_comment or "").strip()
        if not comment:
            raise ValueError("Version comment is required.")

        correlation_id = str(uuid.uuid4())
        with transaction(immediate=True) as conn:
            cursor = conn.cursor()
            recipe = cursor.execute(
                """
                SELECT id, recipe_code, version, status
                FROM recipes
                WHERE id = ?
                """,
                (int(recipe_id),),
            ).fetchone()
            if not recipe:
                raise ValueError("Recipe not found.")

            row = cursor.execute(
                "SELECT COALESCE(MAX(version), 0) FROM recipe_versions WHERE recipe_id = ?",
                (int(recipe_id),),
            ).fetchone()
            next_version = int(row[0] or 0) + 1

            cursor.execute(
                """
                INSERT INTO recipe_versions
                (recipe_id, recipe_code, version, version_comment, created_by)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    int(recipe_id), recipe["recipe_code"], next_version,
                    comment, created_by,
                ),
            )
            recipe_version_id = cursor.lastrowid

            cursor.execute(
                """
                INSERT INTO recipe_version_values
                (recipe_version_id, parameter_definition_id, parameter_value)
                SELECT ?, parameter_definition_id, parameter_value
                FROM recipe_parameter_values
                WHERE recipe_id = ?
                """,
                (recipe_version_id, int(recipe_id)),
            )

            AuditManager.log_event(
                username=created_by,
                role=user_role,
                action="RECIPE_SNAPSHOT_CREATED",
                change_source="RECIPE_VERSION_SNAPSHOT",
                recipe_code=recipe["recipe_code"],
                recipe_version=recipe["version"],
                record_id=recipe_version_id,
                old_value=None,
                new_value=f"Snapshot {next_version}",
                reason=comment,
                correlation_id=correlation_id,
                _connection=conn,
            )

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
        restored_by,
        reason=None,
        user_role="PRODUCTION",
        client_ip=None,
        workstation_name=None,
    ):
        """Restore a non-released recipe snapshot with atomic audit.

        The route already blocks released recipes.  The service repeats the
        lifecycle guard inside the transaction so direct callers cannot bypass
        it.  Unchanged values are skipped and create no parameter audit.
        """
        restore_reason = str(reason or "Restore recipe snapshot").strip()
        if not restore_reason:
            raise ValueError("Restore reason is required.")

        correlation_id = str(uuid.uuid4())
        changed_count = 0
        with transaction(immediate=True) as conn:
            cursor = conn.cursor()
            version = cursor.execute(
                "SELECT * FROM recipe_versions WHERE id = ?",
                (int(recipe_version_id),),
            ).fetchone()
            if not version:
                raise ValueError("Version not found.")

            recipe = cursor.execute(
                """
                SELECT r.*, m.machine_code, s.stage_type
                FROM recipes r
                LEFT JOIN tbm_machines m ON m.id = r.machine_id
                LEFT JOIN machine_stages s ON s.id = r.stage_id
                WHERE r.id = ?
                """,
                (int(version["recipe_id"]),),
            ).fetchone()
            if not recipe:
                raise ValueError("Recipe not found.")
            if str(recipe["status"] or "").upper() == "RELEASED":
                raise ValueError(
                    "Released recipe restore is blocked. Edit the current "
                    "production version directly with audit."
                )

            rows = cursor.execute(
                """
                SELECT
                    rvv.parameter_definition_id,
                    rvv.parameter_value AS snapshot_value,
                    rpv.id AS recipe_parameter_value_id,
                    rpv.parameter_value AS current_value,
                    pd.parameter_name,
                    pd.tag_index
                FROM recipe_version_values rvv
                JOIN recipe_parameter_values rpv
                  ON rpv.recipe_id = ?
                 AND rpv.parameter_definition_id = rvv.parameter_definition_id
                JOIN parameter_definitions pd
                  ON pd.id = rvv.parameter_definition_id
                WHERE rvv.recipe_version_id = ?
                """,
                (int(recipe["id"]), int(recipe_version_id)),
            ).fetchall()

            for row in rows:
                old_value = row["current_value"]
                new_value = row["snapshot_value"]
                try:
                    unchanged = float(old_value) == float(new_value)
                except (TypeError, ValueError):
                    unchanged = old_value == new_value
                if unchanged:
                    continue

                cursor.execute(
                    """
                    UPDATE recipe_parameter_values
                    SET parameter_value = ?, is_modified = 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND recipe_id = ?
                    """,
                    (new_value, row["recipe_parameter_value_id"], recipe["id"]),
                )
                RecipeParameterAuditManager.log_change(
                    recipe_id=recipe["id"],
                    recipe_parameter_value_id=row["recipe_parameter_value_id"],
                    parameter_definition_id=row["parameter_definition_id"],
                    old_value=old_value,
                    new_value=new_value,
                    changed_by=restored_by,
                    recipe_code=recipe["recipe_code"],
                    recipe_version=recipe["version"],
                    parameter_name=row["parameter_name"],
                    tag_index=row["tag_index"],
                    change_source="RECIPE_SNAPSHOT_RESTORE",
                    change_reason=restore_reason,
                    user_role=user_role,
                    client_ip=client_ip,
                    workstation_name=workstation_name,
                    correlation_id=correlation_id,
                    _connection=conn,
                )
                changed_count += 1

            AuditManager.log_event(
                username=restored_by,
                role=user_role,
                action="RECIPE_SNAPSHOT_RESTORED",
                change_source="RECIPE_SNAPSHOT_RESTORE",
                workstation_name=workstation_name,
                client_ip=client_ip,
                recipe_code=recipe["recipe_code"],
                recipe_version=recipe["version"],
                record_id=recipe_version_id,
                old_value=None,
                new_value=f"{changed_count} parameter change(s)",
                reason=restore_reason,
                correlation_id=correlation_id,
                _connection=conn,
            )

        return {
            "success": True,
            "changed_count": changed_count,
            "correlation_id": correlation_id,
        }

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
        """Create an editable production revision atomically from current RELEASED."""
        from database.audit_manager import AuditManager
        from database.recipe_status_history_manager import RecipeStatusHistoryManager

        comment = (version_comment or "Production fast edit").strip()
        correlation_id = uuid.uuid4().hex
        try:
            with transaction(immediate=True) as conn:
                cursor = conn.cursor()
                source = cursor.execute(
                    """
                    SELECT r.*, s.stage_type
                    FROM recipes r
                    JOIN machine_stages s ON s.id=r.stage_id
                    WHERE r.id=?
                    """,
                    (int(recipe_id),),
                ).fetchone()
                if not source:
                    return False, "Recipe Not Found", None
                if str(source["status"] or "").upper() != "RELEASED":
                    return (
                        False,
                        "Only RELEASED recipes can use production fast edit.",
                        recipe_id,
                    )

                current_released = cursor.execute(
                    """
                    SELECT id, version FROM recipes
                    WHERE machine_id=? AND stage_id=?
                      AND UPPER(recipe_code)=UPPER(?) AND status='RELEASED'
                    ORDER BY version DESC, id DESC LIMIT 1
                    """,
                    (source["machine_id"], source["stage_id"], source["recipe_code"]),
                ).fetchone()
                if current_released and int(current_released["id"]) != int(source["id"]):
                    return (
                        False,
                        f"Only current released version can be edited. Open V{current_released['version']} instead.",
                        int(current_released["id"]),
                    )

                open_revision = cursor.execute(
                    """
                    SELECT id, version FROM recipes
                    WHERE machine_id=? AND stage_id=?
                      AND UPPER(recipe_code)=UPPER(?) AND status!='RELEASED'
                    ORDER BY version DESC, id DESC LIMIT 1
                    """,
                    (source["machine_id"], source["stage_id"], source["recipe_code"]),
                ).fetchone()
                if open_revision:
                    return (
                        True,
                        f"Editable revision already exists: V{open_revision['version']}",
                        int(open_revision["id"]),
                    )

                max_version = cursor.execute(
                    """
                    SELECT COALESCE(MAX(version), ?) FROM recipes
                    WHERE machine_id=? AND stage_id=? AND UPPER(recipe_code)=UPPER(?)
                    """,
                    (
                        source["version"], source["machine_id"],
                        source["stage_id"], source["recipe_code"],
                    ),
                ).fetchone()[0]
                next_version = int(max_version) + 1

                cursor.execute(
                    """
                    INSERT INTO recipes
                    (machine_id, stage_id, recipe_code, recipe_name, version,
                     status, created_by)
                    VALUES (?, ?, ?, ?, ?, 'DRAFT', ?)
                    """,
                    (
                        source["machine_id"], source["stage_id"],
                        source["recipe_code"], source["recipe_name"],
                        next_version, created_by,
                    ),
                )
                new_recipe_id = int(cursor.lastrowid)
                cursor.execute(
                    """
                    INSERT INTO recipe_parameter_values
                    (recipe_id, parameter_definition_id, parameter_value, is_modified)
                    SELECT ?, parameter_definition_id, parameter_value, 0
                    FROM recipe_parameter_values WHERE recipe_id=?
                    """,
                    (new_recipe_id, int(recipe_id)),
                )

                phase_columns = {
                    row[1] for row in cursor.execute(
                        "PRAGMA table_info(recipe_phase_control)"
                    )
                }
                has_groups = {"phase_group_code", "phase_group_name", "used"}.issubset(
                    phase_columns
                )
                stage_key = str(source["stage_type"] or "").upper().replace(" ", "_")
                is_second_stage = stage_key in {"SECOND_STAGE", "SECONDSTAGE", "SS"}
                if has_groups:
                    group_filter = (
                        " AND UPPER(COALESCE(phase_group_code, '')) "
                        "IN ('CAP_STRIP_SIDE','BT_SIDE')"
                        if is_second_stage else ""
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
                        (new_recipe_id, int(recipe_id)),
                    )
                elif is_second_stage:
                    raise ValueError(
                        "Second Stage production revision requires migrated phase-group columns."
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO recipe_phase_control
                        (recipe_id, line_no, phase_control_id, stop_option,
                         position_option, sequence_no)
                        SELECT ?, line_no, phase_control_id, stop_option,
                               position_option, sequence_no
                        FROM recipe_phase_control WHERE recipe_id=?
                        """,
                        (new_recipe_id, int(recipe_id)),
                    )

                cursor.execute(
                    """
                    INSERT INTO recipe_versions
                    (recipe_id, recipe_code, version, version_comment, created_by)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        new_recipe_id, source["recipe_code"], next_version,
                        comment, created_by,
                    ),
                )
                RecipeStatusHistoryManager.add_history(
                    recipe_id=new_recipe_id,
                    recipe_code=source["recipe_code"],
                    old_status="",
                    new_status="DRAFT",
                    changed_by=created_by,
                    remarks=(
                        f"Production revision created from V{source['version']}. {comment}"
                    ).strip(),
                    correlation_id=correlation_id,
                    _connection=conn,
                )
                AuditManager.log_event(
                    username=created_by,
                    role=user_role,
                    action="PRODUCTION_REVISION_CREATED",
                    change_source="CANONICAL_RECIPE_VERSION",
                    recipe_code=source["recipe_code"],
                    recipe_version=next_version,
                    record_id=new_recipe_id,
                    old_value=f"V{source['version']} RELEASED",
                    new_value=f"V{next_version} DRAFT",
                    reason=comment,
                    correlation_id=correlation_id,
                    _connection=conn,
                )
            return True, f"Production revision V{next_version} created.", new_recipe_id
        except Exception as exc:
            return (
                False,
                f"Production revision failed and was rolled back ({type(exc).__name__}).",
                None,
            )

    @staticmethod
    def release_production_revision(
        recipe_id,
        released_by,
        remarks,
        user_role="PRODUCTION"
    ):
        """Validate and release a production revision with atomic history/audit."""
        from database.audit_manager import AuditManager
        from database.recipe_status_history_manager import RecipeStatusHistoryManager
        from database.recipe_validation_manager import RecipeValidationManager

        remarks = (remarks or "").strip()
        if not remarks:
            return False, "Production release remarks required."

        validation = RecipeValidationManager.validate_recipe(
            recipe_id, require_released=False
        )
        if not validation["valid"]:
            return (
                False,
                "Validation Failed : " + "; ".join(validation["errors"][:5]),
            )

        correlation_id = uuid.uuid4().hex
        try:
            with transaction(immediate=True) as conn:
                cursor = conn.cursor()
                recipe = cursor.execute(
                    "SELECT * FROM recipes WHERE id=?", (int(recipe_id),)
                ).fetchone()
                if not recipe:
                    return False, "Recipe Not Found"
                if str(recipe["status"] or "").upper() != "DRAFT":
                    return False, "Only DRAFT production revisions can be released directly."

                previous_released = cursor.execute(
                    """
                    SELECT id, version FROM recipes
                    WHERE machine_id=? AND stage_id=?
                      AND UPPER(recipe_code)=UPPER(?)
                      AND version < ? AND status='RELEASED'
                    ORDER BY version DESC, id DESC LIMIT 1
                    """,
                    (
                        recipe["machine_id"], recipe["stage_id"],
                        recipe["recipe_code"], recipe["version"],
                    ),
                ).fetchone()
                if not previous_released:
                    return (
                        False,
                        "Direct production release is allowed only for revisions created from an existing RELEASED recipe.",
                    )

                current_released = cursor.execute(
                    """
                    SELECT id, version FROM recipes
                    WHERE machine_id=? AND stage_id=?
                      AND UPPER(recipe_code)=UPPER(?) AND status='RELEASED'
                    ORDER BY version DESC, id DESC LIMIT 1
                    """,
                    (
                        recipe["machine_id"], recipe["stage_id"],
                        recipe["recipe_code"],
                    ),
                ).fetchone()
                if current_released and int(current_released["version"]) > int(recipe["version"]):
                    return (
                        False,
                        f"Cannot release V{recipe['version']} because V{current_released['version']} is already current.",
                    )

                cursor.execute(
                    "UPDATE recipes SET status='RELEASED', updated_at=CURRENT_TIMESTAMP WHERE id=? AND status='DRAFT'",
                    (int(recipe_id),),
                )
                if cursor.rowcount != 1:
                    raise RuntimeError("Recipe status changed concurrently.")

                RecipeStatusHistoryManager.add_history(
                    recipe_id=recipe_id,
                    recipe_code=recipe["recipe_code"],
                    old_status="DRAFT",
                    new_status="RELEASED",
                    changed_by=released_by,
                    remarks=("Production fast release. " + remarks).strip(),
                    correlation_id=correlation_id,
                    _connection=conn,
                )
                AuditManager.log_event(
                    username=released_by,
                    role=user_role,
                    action="PRODUCTION_REVISION_RELEASED",
                    change_source="CANONICAL_RECIPE_VERSION",
                    recipe_code=recipe["recipe_code"],
                    recipe_version=recipe["version"],
                    record_id=recipe_id,
                    old_value="DRAFT",
                    new_value="RELEASED",
                    reason=remarks,
                    correlation_id=correlation_id,
                    _connection=conn,
                )
            return True, f"Production revision V{recipe['version']} released."
        except Exception as exc:
            return (
                False,
                f"Production revision release failed and was rolled back ({type(exc).__name__}).",
            )
