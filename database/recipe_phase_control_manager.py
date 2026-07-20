import uuid

from database.database import (
    get_connection,
    transaction,
)
from database.phase_template_manager import PhaseTemplateManager


class RecipePhaseControlManager:

    SECOND_STAGE_RECIPE_GROUPS = (
        "CAP_STRIP_SIDE",
        "BT_SIDE",
    )

    PHASE_GROUP_ORDER = {
        "MAIN": 0,
        "CAP_STRIP_SIDE": 1,
        "BT_SIDE": 2,
    }

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
    def _is_first_stage(stage_type):
        return (
            str(stage_type or "").strip().upper().replace(" ", "_")
            in {"FIRST_STAGE", "FIRSTSTAGE", "FS"}
        )

    @staticmethod
    def _is_second_stage(stage_type):
        return (
            str(stage_type or "").strip().upper().replace(" ", "_")
            in {"SECOND_STAGE", "SECONDSTAGE", "SS"}
        )

    @staticmethod
    def _recipe_controlled_group_codes(stage_type):
        if RecipePhaseControlManager._is_first_stage(stage_type):
            return {"MAIN"}
        if RecipePhaseControlManager._is_second_stage(stage_type):
            return set(RecipePhaseControlManager.SECOND_STAGE_RECIPE_GROUPS)
        return None

    @staticmethod
    def _is_recipe_controlled_group(stage_type, group_code):
        allowed_codes = RecipePhaseControlManager._recipe_controlled_group_codes(
            stage_type
        )
        if allowed_codes is None:
            return True
        normalized_code = str(group_code or "MAIN").strip().upper()
        return normalized_code in allowed_codes

    @staticmethod
    def _filter_recipe_controlled_groups(stage_type, groups):
        allowed_codes = RecipePhaseControlManager._recipe_controlled_group_codes(
            stage_type
        )
        if allowed_codes is None:
            return list(groups)
        return [
            group for group in groups
            if str(group["phase_group_code"] or "MAIN").strip().upper()
            in allowed_codes
        ]

    @staticmethod
    def _recipe_phase_group_filter(stage_type, column_sql):
        allowed_codes = RecipePhaseControlManager._recipe_controlled_group_codes(
            stage_type
        )
        if not allowed_codes:
            return "", []
        ordered_codes = [
            code for code in ("MAIN", "CAP_STRIP_SIDE", "BT_SIDE")
            if code in allowed_codes
        ]
        placeholders = ", ".join("?" for _ in ordered_codes)
        return (
            f" AND UPPER(COALESCE({column_sql}, 'MAIN')) IN ({placeholders})",
            ordered_codes,
        )

    @staticmethod
    def _phase_group_sort_value(group_code):
        return RecipePhaseControlManager.PHASE_GROUP_ORDER.get(
            str(group_code or "MAIN").strip().upper(),
            99,
        )

    @staticmethod
    def _recipe_stage_type(cursor, recipe_id):
        row = cursor.execute(
            """
            SELECT ms.stage_type
            FROM recipes r
            LEFT JOIN machine_stages ms
                ON ms.id = r.stage_id
            WHERE r.id = ?
            """,
            (recipe_id,),
        ).fetchone()
        return (row["stage_type"] if row else "") or ""

    @staticmethod
    def get_expected_phase_row_count(stage_id=None, stage_type=None):
        """
        Return the required number of recipe phase-control rows.

        The phase master is a dropdown list; recipe rows are fixed slots:
        first stage has one 12-row phase-control block, while second stage
        has six rows for each active stage-specific phase group.
        """
        resolved_stage_type = stage_type or ""
        conn = None

        try:
            conn = get_connection()
            cursor = conn.cursor()

            if not resolved_stage_type and stage_id:
                row = cursor.execute(
                    """
                    SELECT stage_type
                    FROM machine_stages
                    WHERE id = ?
                    """,
                    (stage_id,)
                ).fetchone()
                resolved_stage_type = (row["stage_type"] if row else "") or ""

            if RecipePhaseControlManager._is_first_stage(resolved_stage_type):
                return 12

            PhaseTemplateManager.ensure_schema()

            group_count = 0
            if (
                stage_id
                and RecipePhaseControlManager._table_exists(
                    cursor,
                    "phase_control_group_master"
                )
            ):
                rows = cursor.execute(
                    """
                    SELECT phase_group_code
                    FROM phase_control_group_master
                    WHERE machine_stage_id = ?
                        AND COALESCE(active, 1) = 1
                    """,
                    (stage_id,)
                ).fetchall()
                group_count = len(
                    RecipePhaseControlManager._filter_recipe_controlled_groups(
                        resolved_stage_type,
                        rows,
                    )
                )

            if group_count > 0:
                return group_count * 6

            if RecipePhaseControlManager._is_second_stage(resolved_stage_type):
                return 12

            return 12

        finally:
            if conn:
                conn.close()

    @staticmethod
    def _normalize_first_stage_recipe_rows(cursor, recipe_id):
        if not RecipePhaseControlManager._is_first_stage(
            RecipePhaseControlManager._recipe_stage_type(cursor, recipe_id)
        ):
            return

        cols = RecipePhaseControlManager._columns(cursor, "recipe_phase_control")
        if not {"phase_group_code", "phase_group_name"}.issubset(cols):
            return

        main_count = cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM recipe_phase_control
            WHERE recipe_id = ?
                AND UPPER(COALESCE(phase_group_code, 'MAIN')) = 'MAIN'
            """,
            (recipe_id,),
        ).fetchone()

        if int(main_count["total"] or 0) == 0:
            cursor.execute(
                """
                UPDATE recipe_phase_control
                SET phase_group_code = 'MAIN',
                    phase_group_name = 'Phase Control'
                WHERE recipe_id = ?
                """,
                (recipe_id,),
            )

    @staticmethod
    def _create_group_phase_rows(cursor, recipe_id, machine_id, stage_id):
        """
        Create stage-wise phase-control recipe slots from the stage template.

        The phase master is a dropdown/template list. It must not create one
        recipe row per phase option. New recipes get Empty Phase slots, then the
        user chooses from the template dropdown for that machine/stage.
        """
        PhaseTemplateManager.ensure_schema()

        if not RecipePhaseControlManager._table_exists(cursor, "phase_control_group_master"):
            return False

        groups = cursor.execute(
            """
            SELECT
                phase_group_code,
                phase_group_name,
                display_order
            FROM phase_control_group_master
            WHERE machine_stage_id = ? AND COALESCE(active, 1) = 1
            ORDER BY display_order, phase_group_name
            """,
            (stage_id,)
        ).fetchall()

        if not groups:
            return False

        stage_row = cursor.execute(
            """
            SELECT stage_type
            FROM machine_stages
            WHERE id = ?
            """,
            (stage_id,)
        ).fetchone()
        stage_type = (stage_row["stage_type"] if stage_row else "") or ""
        stage_upper = stage_type.upper().replace(" ", "_")

        if stage_upper in {"FIRST_STAGE", "FIRSTSTAGE", "FS"}:
            slot_count = 12
            groups = [
                group for group in groups
                if (group["phase_group_code"] or "MAIN").upper() == "MAIN"
            ]
        elif stage_upper in {"SECOND_STAGE", "SECONDSTAGE", "SS"}:
            slot_count = 6
            groups = RecipePhaseControlManager._filter_recipe_controlled_groups(
                stage_type,
                groups,
            )
        else:
            slot_count = 6

        if not groups:
            return False

        cols = RecipePhaseControlManager._columns(cursor, "recipe_phase_control")
        has_group_cols = {"phase_group_code", "phase_group_name", "used"}.issubset(cols)
        created_count = 0

        for group in groups:
            group_code = group["phase_group_code"] or "MAIN"
            group_name = group["phase_group_name"] or "Phase Control"

            empty_phase = cursor.execute(
                """
                SELECT id
                FROM phase_control_master
                WHERE
                    machine_stage_id = ?
                    AND COALESCE(phase_group_code, 'MAIN') = ?
                    AND UPPER(COALESCE(phase_control_key, phase_control_name)) = 'EMPTY PHASE'
                ORDER BY COALESCE(display_order, 999), id
                LIMIT 1
                """,
                (stage_id, group_code)
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
                        phase_control_key,
                        plc_phase_code,
                        description,
                        display_order,
                        active
                    )
                    VALUES (?, ?, ?, ?, 'Empty Phase', 'EMPTY PHASE', 0, 'Unused phase-control slot', 999, 1)
                    """,
                    (
                        stage_type,
                        stage_id,
                        group_code,
                        group_name,
                    )
                )
                empty_phase_id = cursor.lastrowid

            for line_no in range(1, slot_count + 1):
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
                        VALUES (?, ?, ?, ?, ?, 'No', 'No', ?, 1)
                        """,
                        (
                            recipe_id,
                            group_code,
                            group_name,
                            line_no,
                            empty_phase_id,
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
                        VALUES (?, ?, ?, 'No', 'No', ?)
                        """,
                        (
                            recipe_id,
                            line_no,
                            empty_phase_id,
                            line_no,
                        )
                    )
                created_count += 1

        print(
            f"Stage phase template rows created for Recipe ID {recipe_id}: "
            f"{created_count} Empty Phase slot(s) across {len(groups)} group(s)"
        )
        return created_count > 0


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

        PhaseTemplateManager.ensure_schema()

        cursor.execute(
            """
            SELECT id

            FROM phase_control_master

            WHERE UPPER(COALESCE(phase_control_key, phase_control_name)) =
            'EMPTY PHASE'
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
        stage_type = RecipePhaseControlManager._recipe_stage_type(
            cursor,
            recipe_id,
        )
        is_first_stage = RecipePhaseControlManager._is_first_stage(stage_type)
        group_filter_sql, group_filter_params = (
            RecipePhaseControlManager._recipe_phase_group_filter(
                stage_type,
                "rpc.phase_group_code",
            )
        )

        if has_group_cols and is_first_stage:
            RecipePhaseControlManager._normalize_first_stage_recipe_rows(
                cursor,
                recipe_id,
            )
            conn.commit()

        if has_group_cols:
            cursor.execute(
                f"""
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

                    {group_filter_sql}

                    AND (
                        ? = 0
                        OR rpc.line_no BETWEEN 1 AND 12
                    )

                ORDER BY
                    CASE COALESCE(rpc.phase_group_code, 'MAIN')
                        WHEN 'MAIN' THEN 0
                        WHEN 'CAP_STRIP_SIDE' THEN 1
                        WHEN 'BT_SIDE' THEN 2
                        ELSE 99
                    END,
                    rpc.line_no
                """,
                tuple(
                    [recipe_id]
                    + group_filter_params
                    + [1 if is_first_stage else 0]
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

        result = [dict(row) for row in rows]
        if is_first_stage:
            unique_rows = {}
            for row in result:
                try:
                    line_no = int(row.get("line_no") or 0)
                except Exception:
                    line_no = 0
                if line_no < 1 or line_no > 12 or line_no in unique_rows:
                    continue
                unique_rows[line_no] = row
            result = [unique_rows[line_no] for line_no in sorted(unique_rows)]

        return result

    @staticmethod
    def save_phase_sequence(
        recipe_id,
        selections,
        changed_by,
        user_role,
        change_reason,
        change_source="RECIPE_PHASE_CONTROL_EDIT",
        client_ip=None,
        workstation_name=None,
    ):
        """Validate, save and audit a complete phase sequence atomically."""
        from database.audit_manager import AuditManager

        reason = (change_reason or "").strip()
        if not reason:
            return {"success": False, "message": "Phase change reason is required."}

        correlation_id = uuid.uuid4().hex
        changed_rows = []
        try:
            with transaction(immediate=True) as conn:
                cursor = conn.cursor()
                recipe = cursor.execute(
                    """
                    SELECT r.*, s.stage_type, m.machine_code,
                           CASE
                               WHEN r.status='RELEASED' AND r.id=(
                                   SELECT x.id FROM recipes x
                                   WHERE x.machine_id=r.machine_id
                                     AND x.stage_id=r.stage_id
                                     AND UPPER(x.recipe_code)=UPPER(r.recipe_code)
                                     AND x.status='RELEASED'
                                   ORDER BY x.version DESC, x.id DESC LIMIT 1
                               ) THEN 1 ELSE 0
                           END AS is_current_released
                    FROM recipes r
                    LEFT JOIN machine_stages s ON s.id=r.stage_id
                    LEFT JOIN tbm_machines m ON m.id=r.machine_id
                    WHERE r.id=?
                    """,
                    (int(recipe_id),),
                ).fetchone()
                if not recipe:
                    return {"success": False, "message": "Recipe not found."}
                if recipe["status"] == "RELEASED" and int(recipe["is_current_released"] or 0) != 1:
                    return {
                        "success": False,
                        "message": "Historical released recipe phase controls are read-only.",
                    }

                stage_key = str(recipe["stage_type"] or "").strip().upper().replace(" ", "_")
                is_second_stage = stage_key in {"SECOND_STAGE", "SECONDSTAGE", "SS"}
                rows = cursor.execute(
                    """
                    SELECT rpc.*, old_pcm.phase_control_name AS old_phase_name
                    FROM recipe_phase_control rpc
                    LEFT JOIN phase_control_master old_pcm ON old_pcm.id=rpc.phase_control_id
                    WHERE rpc.recipe_id=?
                    ORDER BY rpc.phase_group_code, rpc.line_no
                    """,
                    (int(recipe_id),),
                ).fetchall()

                for row in rows:
                    group_code = (row["phase_group_code"] or "MAIN").upper()
                    if is_second_stage and group_code not in RecipePhaseControlManager.SECOND_STAGE_RECIPE_GROUPS:
                        continue
                    posted = selections.get(str(row["id"])) or selections.get(int(row["id"]))
                    if not posted:
                        return {
                            "success": False,
                            "message": f"Missing phase selection for {group_code} line {row['line_no']}.",
                        }

                    new_phase_id = int(posted.get("phase_control_id"))
                    allowed = cursor.execute(
                        """
                        SELECT id, phase_control_name
                        FROM phase_control_master
                        WHERE id=?
                          AND machine_stage_id=?
                          AND UPPER(COALESCE(phase_group_code, 'MAIN'))=?
                          AND COALESCE(active, 1)=1
                        """,
                        (new_phase_id, recipe["stage_id"], group_code),
                    ).fetchone()
                    if not allowed:
                        return {
                            "success": False,
                            "message": f"Selected phase is not allowed for {group_code} line {row['line_no']}.",
                        }

                    old_phase_id = row["phase_control_id"]
                    old_stop = row["stop_option"]
                    old_position = row["position_option"]
                    if is_second_stage:
                        # Final contract: SS recipe data is selection-only. Legacy
                        # columns remain in the schema only for historical compatibility.
                        new_stop = None
                        new_position = None
                    else:
                        new_stop = posted.get("stop_option") or "No"
                        new_position = posted.get("position_option") or "No"

                    changed = (
                        int(old_phase_id or 0) != new_phase_id
                        or (not is_second_stage and (old_stop != new_stop or old_position != new_position))
                    )
                    if not changed:
                        continue

                    cursor.execute(
                        """
                        UPDATE recipe_phase_control
                        SET phase_control_id=?, stop_option=?, position_option=?,
                            sequence_no=?, updated_at=CURRENT_TIMESTAMP,
                            row_version=COALESCE(row_version, 0)+1
                        WHERE id=?
                        """,
                        (
                            new_phase_id, new_stop, new_position, row["line_no"], row["id"]
                        ),
                    )
                    cursor.execute(
                        """
                        INSERT INTO recipe_phase_control_audit
                        (
                            correlation_id, recipe_id, phase_row_id, phase_group_code,
                            line_no, old_phase_control_id, new_phase_control_id,
                            old_phase_name, new_phase_name, old_stop_option,
                            new_stop_option, old_position_option, new_position_option,
                            changed_by, user_role, change_source, change_reason
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            correlation_id, recipe_id, row["id"], group_code, row["line_no"],
                            old_phase_id, new_phase_id, row["old_phase_name"],
                            allowed["phase_control_name"],
                            None if is_second_stage else old_stop,
                            None if is_second_stage else new_stop,
                            None if is_second_stage else old_position,
                            None if is_second_stage else new_position,
                            changed_by, user_role, change_source, reason,
                        ),
                    )
                    changed_rows.append({
                        "row_id": row["id"],
                        "group": group_code,
                        "line_no": row["line_no"],
                        "old": row["old_phase_name"],
                        "new": allowed["phase_control_name"],
                    })

                if changed_rows:
                    AuditManager.log_event(
                        username=changed_by,
                        role=user_role,
                        action="RECIPE_PHASE_SEQUENCE_CHANGED",
                        change_source=change_source,
                        workstation_name=workstation_name,
                        client_ip=client_ip,
                        recipe_code=recipe["recipe_code"],
                        recipe_version=recipe["version"],
                        record_id=int(recipe_id),
                        old_value=f"{len(changed_rows)} previous phase row(s)",
                        new_value=f"{len(changed_rows)} updated phase row(s)",
                        reason=reason,
                        correlation_id=correlation_id,
                        _connection=conn,
                    )

            return {
                "success": True,
                "changed": bool(changed_rows),
                "changed_count": len(changed_rows),
                "changed_rows": changed_rows,
                "correlation_id": correlation_id,
                "message": (
                    f"Phase Control saved and audited: {len(changed_rows)} row(s) changed."
                    if changed_rows
                    else "No phase-control change detected; no audit was created."
                ),
            }
        except Exception as exc:
            return {
                "success": False,
                "message": "Phase-control save failed and was rolled back.",
                "error_type": type(exc).__name__,
                "correlation_id": correlation_id,
            }

    @staticmethod
    def update_phase_row(*_args, **_kwargs):
        raise RuntimeError(
            "Direct phase-row mutation is blocked. Use save_phase_sequence so "
            "validation, locking and audit remain atomic."
        )

    @staticmethod
    def ensure_group_empty_phase_slots(

        recipe_id,

        stage_type,

        stage_id,

        min_slots=6

    ):

        PhaseTemplateManager.ensure_schema()

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

        if RecipePhaseControlManager._is_first_stage(stage_type):
            groups = [
                group for group in groups
                if (group["phase_group_code"] or "MAIN").upper() == "MAIN"
            ]
            min_slots = 12
        elif RecipePhaseControlManager._is_second_stage(stage_type):
            groups = RecipePhaseControlManager._filter_recipe_controlled_groups(
                stage_type,
                groups,
            )
            min_slots = 6

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
                    AND UPPER(COALESCE(phase_control_key, phase_control_name)) = 'EMPTY PHASE'
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
                        phase_control_key,
                        plc_phase_code,
                        description,
                        display_order,
                        active
                    )
                    VALUES (?, ?, ?, ?, 'Empty Phase', 'EMPTY PHASE', 0, 'Unused phase-control slot', 999, 1)
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
        source_stage_type = RecipePhaseControlManager._recipe_stage_type(
            cursor,
            source_recipe_id,
        )
        group_filter_sql, group_filter_params = (
            RecipePhaseControlManager._recipe_phase_group_filter(
                source_stage_type,
                "phase_group_code",
            )
        )

        cursor.execute(
            f"""
            SELECT *

            FROM recipe_phase_control

            WHERE recipe_id = ?

                {group_filter_sql}

            ORDER BY
                CASE COALESCE(phase_group_code, 'MAIN')
                    WHEN 'MAIN' THEN 0
                    WHEN 'CAP_STRIP_SIDE' THEN 1
                    WHEN 'BT_SIDE' THEN 2
                    ELSE 99
                END,
                line_no
            """,
            tuple([source_recipe_id] + group_filter_params)
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

        stage_type = RecipePhaseControlManager._recipe_stage_type(
            cursor,
            recipe_id,
        )
        group_filter_sql, group_filter_params = (
            RecipePhaseControlManager._recipe_phase_group_filter(
                stage_type,
                "rpc.phase_group_code",
            )
        )

        cursor.execute(
            f"""
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

                {group_filter_sql}

            ORDER BY
                CASE COALESCE(rpc.phase_group_code, 'MAIN')
                    WHEN 'MAIN' THEN 0
                    WHEN 'CAP_STRIP_SIDE' THEN 1
                    WHEN 'BT_SIDE' THEN 2
                    ELSE 99
                END,
                rpc.line_no
            """,
            tuple([recipe_id] + group_filter_params)
        )

        rows = cursor.fetchall()

        conn.close()

        return [

            dict(row)

            for row in rows

        ]
