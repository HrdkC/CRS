import re

from database.database import get_connection
from database.schema_guard import require_table


class PhaseTemplateManager:
    """Stage-wise phase template helper.

    Phase display text is preserved exactly as the module/stage template owns it.
    Duplicate control uses a normalized key, so different letter case does not
    create duplicate phase options inside the same stage/group.
    """

    PHASE_CODE_BASE_BY_GROUP = {
        "APPLICATION_SIDE": 100,
        "CAP_STRIP_SIDE": 200,
        "BT_SIDE": 300,
        "SHAPING_SIDE": 400,
        "MAIN": 900,
    }

    @staticmethod
    def _columns(cursor, table_name):
        rows = cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {row["name"] for row in rows}

    @staticmethod
    def ensure_schema():
        return require_table(
            "phase_control_master",
            {
                "phase_control_name", "phase_control_key", "plc_phase_code",
                "machine_stage_id", "phase_group_code", "active",
            },
        )

    @staticmethod
    def clean_display_name(value):
        text = str(value or "").strip()
        text = re.sub(r"\s+", " ", text)
        return text

    @staticmethod
    def phase_key(value):
        text = PhaseTemplateManager.clean_display_name(value)
        return text.upper()

    @staticmethod
    def group_code(value):
        text = str(value or "MAIN").strip().upper()
        text = re.sub(r"[^A-Z0-9]+", "_", text)
        text = re.sub(r"_+", "_", text).strip("_")
        return text or "MAIN"

    @staticmethod
    def _phase_code_from_name(group_code, phase_name, fallback_order=1):
        key = PhaseTemplateManager.phase_key(phase_name)
        if key == "EMPTY PHASE":
            return 0
        base = PhaseTemplateManager.PHASE_CODE_BASE_BY_GROUP.get(
            PhaseTemplateManager.group_code(group_code),
            900,
        )
        try:
            number = int(fallback_order or 1)
        except Exception:
            number = 1
        return base + max(number, 1)

    @staticmethod
    def sync_phase_keys(machine_stage_id=None):
        conn = get_connection()
        cur = conn.cursor()
        conditions = []
        params = []
        if machine_stage_id:
            conditions.append("machine_stage_id = ?")
            params.append(machine_stage_id)

        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)

        rows = cur.execute(
            f"""
            SELECT id, phase_control_name, phase_group_code, display_order, plc_phase_code
            FROM phase_control_master
            {where}
            """,
            tuple(params),
        ).fetchall()

        for row in rows:
            key = PhaseTemplateManager.phase_key(row["phase_control_name"])
            plc_code = row["plc_phase_code"]
            if plc_code is None:
                plc_code = PhaseTemplateManager._phase_code_from_name(
                    row["phase_group_code"],
                    row["phase_control_name"],
                    row["display_order"],
                )
            cur.execute(
                """
                UPDATE phase_control_master
                SET phase_control_key = ?, plc_phase_code = ?
                WHERE id = ?
                """,
                (key, plc_code, row["id"]),
            )

        conn.commit()
        conn.close()

    @staticmethod
    def get_duplicate_report(machine_stage_id):
        PhaseTemplateManager.ensure_schema()
        conn = get_connection()
        cur = conn.cursor()

        rows = cur.execute(
            """
            SELECT *
            FROM phase_control_master
            WHERE machine_stage_id = ?
            ORDER BY
                COALESCE(phase_group_code, 'MAIN'),
                COALESCE(display_order, 0),
                id
            """,
            (machine_stage_id,),
        ).fetchall()
        conn.close()

        by_name_key = {}
        by_code_key = {}
        for row in rows:
            data = dict(row)
            if int(data.get("active", 1) or 0) == 1:
                group = PhaseTemplateManager.group_code(data.get("phase_group_code"))
                name_key = data.get("phase_control_key") or PhaseTemplateManager.phase_key(data.get("phase_control_name"))
                by_name_key.setdefault((group, name_key), []).append(data)

                plc_code = data.get("plc_phase_code")
                if plc_code not in (None, ""):
                    by_code_key.setdefault((group, int(plc_code)), []).append(data)

        duplicate_names = []
        for (group, name_key), items in sorted(by_name_key.items()):
            if name_key and len(items) > 1:
                duplicate_names.append(
                    {
                        "group_code": group,
                        "phase_key": name_key,
                        "count": len(items),
                        "rows": items,
                    }
                )

        duplicate_codes = []
        for (group, plc_code), items in sorted(by_code_key.items()):
            if plc_code != 0 and len(items) > 1:
                duplicate_codes.append(
                    {
                        "group_code": group,
                        "plc_phase_code": plc_code,
                        "count": len(items),
                        "rows": items,
                    }
                )

        return {
            "duplicate_names": duplicate_names,
            "duplicate_codes": duplicate_codes,
            "duplicate_name_count": len(duplicate_names),
            "duplicate_code_count": len(duplicate_codes),
        }

    @staticmethod
    def _validate_template_rows(rows):
        errors = []
        seen_names = {}
        seen_codes = {}

        for row in rows:
            phase_id = row.get("id")
            active = 1 if int(row.get("active", 0) or 0) == 1 else 0
            group = PhaseTemplateManager.group_code(row.get("phase_group_code"))
            name = PhaseTemplateManager.clean_display_name(row.get("phase_control_name"))
            key = PhaseTemplateManager.phase_key(name)

            if not name:
                errors.append(f"Phase ID {phase_id}: phase name is required.")
                continue

            plc_code = row.get("plc_phase_code")
            if plc_code not in (None, ""):
                try:
                    plc_code = int(plc_code)
                except Exception:
                    errors.append(f"{name}: PLC phase code must be an integer.")
                    plc_code = None

            if active:
                name_tuple = (group, key)
                if name_tuple in seen_names:
                    errors.append(
                        f"Duplicate phase name in {group}: {name} matches {seen_names[name_tuple]} ignoring case."
                    )
                else:
                    seen_names[name_tuple] = name

                if plc_code not in (None, ""):
                    code_tuple = (group, int(plc_code))
                    if int(plc_code) != 0 and code_tuple in seen_codes:
                        errors.append(
                            f"Duplicate PLC phase code in {group}: {plc_code} used by {name} and {seen_codes[code_tuple]}."
                        )
                    else:
                        seen_codes[code_tuple] = name

        return errors

    @staticmethod
    def save_phase_rows(machine_stage_id, rows):
        PhaseTemplateManager.ensure_schema()
        errors = PhaseTemplateManager._validate_template_rows(rows)
        if errors:
            return False, errors, 0

        conn = get_connection()
        cur = conn.cursor()
        changed_count = 0
        try:
            cur.execute("BEGIN")
            for raw in rows:
                phase_id = int(raw.get("id"))
                name = PhaseTemplateManager.clean_display_name(raw.get("phase_control_name"))
                key = PhaseTemplateManager.phase_key(name)
                description = PhaseTemplateManager.clean_display_name(raw.get("description"))
                display_order = int(raw.get("display_order") or 0)
                active = 1 if int(raw.get("active", 0) or 0) == 1 else 0
                plc_code_raw = raw.get("plc_phase_code")
                plc_code = int(plc_code_raw) if plc_code_raw not in (None, "") else None

                old = cur.execute(
                    """
                    SELECT phase_control_name, phase_control_key, description,
                           display_order, active, plc_phase_code
                    FROM phase_control_master
                    WHERE id = ? AND machine_stage_id = ?
                    """,
                    (phase_id, machine_stage_id),
                ).fetchone()
                if not old:
                    continue

                new_tuple = (name, key, description, display_order, active, plc_code)
                old_tuple = (
                    old["phase_control_name"],
                    old["phase_control_key"],
                    old["description"],
                    old["display_order"],
                    old["active"],
                    old["plc_phase_code"],
                )
                if new_tuple == old_tuple:
                    continue

                cur.execute(
                    """
                    UPDATE phase_control_master
                    SET
                        phase_control_name = ?,
                        phase_control_key = ?,
                        description = ?,
                        display_order = ?,
                        active = ?,
                        plc_phase_code = ?
                    WHERE id = ? AND machine_stage_id = ?
                    """,
                    (
                        name,
                        key,
                        description,
                        display_order,
                        active,
                        plc_code,
                        phase_id,
                        machine_stage_id,
                    ),
                )
                changed_count += cur.rowcount

            conn.commit()
        except Exception as exc:
            conn.rollback()
            conn.close()
            return False, [str(exc)], 0

        conn.close()
        return True, [], changed_count

    @staticmethod
    def create_phase(machine_stage_id, stage_type, group_code, group_name, phase_name, description="", display_order=0, plc_phase_code=None):
        PhaseTemplateManager.ensure_schema()
        phase_name = PhaseTemplateManager.clean_display_name(phase_name)
        description = PhaseTemplateManager.clean_display_name(description or phase_name)
        group_code = PhaseTemplateManager.group_code(group_code)
        phase_key = PhaseTemplateManager.phase_key(phase_name)

        if not phase_name:
            return False, "Phase name is required.", None

        if plc_phase_code in (None, ""):
            plc_phase_code = PhaseTemplateManager._phase_code_from_name(
                group_code,
                phase_name,
                display_order,
            )
        else:
            try:
                plc_phase_code = int(plc_phase_code)
            except Exception:
                return False, "PLC phase code must be an integer.", None

        conn = get_connection()
        cur = conn.cursor()
        existing = cur.execute(
            """
            SELECT id, phase_control_name
            FROM phase_control_master
            WHERE machine_stage_id = ?
              AND UPPER(COALESCE(phase_group_code, 'MAIN')) = UPPER(?)
              AND COALESCE(active, 1) = 1
              AND UPPER(COALESCE(phase_control_key, phase_control_name)) = UPPER(?)
            """,
            (machine_stage_id, group_code, phase_key),
        ).fetchone()
        if existing:
            conn.close()
            return False, f"Phase already exists in this group: {existing['phase_control_name']}", None

        if plc_phase_code != 0:
            duplicate_code = cur.execute(
                """
                SELECT id, phase_control_name
                FROM phase_control_master
                WHERE machine_stage_id = ?
                  AND UPPER(COALESCE(phase_group_code, 'MAIN')) = UPPER(?)
                  AND COALESCE(active, 1) = 1
                  AND plc_phase_code = ?
                """,
                (machine_stage_id, group_code, plc_phase_code),
            ).fetchone()
            if duplicate_code:
                conn.close()
                return False, f"PLC phase code {plc_phase_code} already used by {duplicate_code['phase_control_name']}.", None

        cur.execute(
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
                description,
                display_order,
                active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                machine_stage_id,
                stage_type,
                group_code,
                group_name,
                phase_name,
                phase_key,
                plc_phase_code,
                description,
                int(display_order or 0),
            ),
        )
        phase_id = cur.lastrowid
        conn.commit()
        conn.close()
        return True, "Phase option created.", phase_id

    @staticmethod
    def save_group_template_lines(machine_stage_id, stage_type, group_code, group_name, lines, deactivate_missing=False):
        PhaseTemplateManager.ensure_schema()
        group_code = PhaseTemplateManager.group_code(group_code)
        cleaned_lines = []
        seen = set()
        errors = []

        for line_number, raw in enumerate(lines, start=1):
            name = PhaseTemplateManager.clean_display_name(raw)
            if not name:
                continue
            key = PhaseTemplateManager.phase_key(name)
            if key in seen:
                errors.append(f"Line {line_number}: duplicate phase name ignoring case: {name}")
                continue
            seen.add(key)
            cleaned_lines.append(name)

        if not cleaned_lines:
            errors.append("At least one phase name is required.")

        if errors:
            return False, errors, {"updated": 0, "inserted": 0, "deactivated": 0}

        conn = get_connection()
        cur = conn.cursor()
        updated = 0
        inserted = 0
        deactivated = 0
        try:
            cur.execute("BEGIN")
            existing_rows = cur.execute(
                """
                SELECT *
                FROM phase_control_master
                WHERE machine_stage_id = ?
                  AND UPPER(COALESCE(phase_group_code, 'MAIN')) = UPPER(?)
                ORDER BY COALESCE(display_order, 0), id
                """,
                (machine_stage_id, group_code),
            ).fetchall()
            by_key = {}
            for row in existing_rows:
                key = row["phase_control_key"] or PhaseTemplateManager.phase_key(row["phase_control_name"])
                by_key.setdefault(key, []).append(dict(row))

            active_keys = set()
            for index, name in enumerate(cleaned_lines, start=1):
                key = PhaseTemplateManager.phase_key(name)
                active_keys.add(key)
                existing_group = by_key.get(key) or []

                plc_code = PhaseTemplateManager._phase_code_from_name(group_code, name, index)
                if existing_group:
                    keep = existing_group[0]
                    if keep.get("plc_phase_code") is not None:
                        plc_code = keep.get("plc_phase_code")
                    cur.execute(
                        """
                        UPDATE phase_control_master
                        SET
                            phase_control_name = ?,
                            phase_control_key = ?,
                            phase_group_name = ?,
                            description = COALESCE(NULLIF(description, ''), ?),
                            display_order = ?,
                            active = 1,
                            plc_phase_code = ?
                        WHERE id = ?
                        """,
                        (
                            name,
                            key,
                            group_name,
                            name,
                            index,
                            plc_code,
                            keep["id"],
                        ),
                    )
                    updated += cur.rowcount

                    for duplicate in existing_group[1:]:
                        cur.execute(
                            """
                            UPDATE recipe_phase_control
                            SET phase_control_id = ?
                            WHERE phase_control_id = ?
                            """,
                            (keep["id"], duplicate["id"]),
                        )
                        cur.execute(
                            """
                            UPDATE phase_control_master
                            SET active = 0,
                                display_order = ?,
                                description = COALESCE(NULLIF(description, ''), 'Deactivated duplicate by phase template cleanup')
                            WHERE id = ?
                            """,
                            (9999 + index, duplicate["id"]),
                        )
                        deactivated += cur.rowcount
                else:
                    cur.execute(
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
                            description,
                            display_order,
                            active
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                        """,
                        (
                            machine_stage_id,
                            stage_type,
                            group_code,
                            group_name,
                            name,
                            key,
                            plc_code,
                            name,
                            index,
                        ),
                    )
                    inserted += 1

            if deactivate_missing:
                for row in existing_rows:
                    key = row["phase_control_key"] or PhaseTemplateManager.phase_key(row["phase_control_name"])
                    if key not in active_keys and int(row["active"] or 0) == 1:
                        cur.execute(
                            """
                            UPDATE phase_control_master
                            SET active = 0
                            WHERE id = ?
                            """,
                            (row["id"],),
                        )
                        deactivated += cur.rowcount

            conn.commit()
        except Exception as exc:
            conn.rollback()
            conn.close()
            return False, [str(exc)], {"updated": 0, "inserted": 0, "deactivated": 0}

        conn.close()
        return True, [], {"updated": updated, "inserted": inserted, "deactivated": deactivated}

    @staticmethod
    def merge_case_duplicates(machine_stage_id):
        PhaseTemplateManager.ensure_schema()
        conn = get_connection()
        cur = conn.cursor()
        changed = {
            "merged": 0,
            "deactivated": 0,
        }
        try:
            cur.execute("BEGIN")
            rows = cur.execute(
                """
                SELECT *
                FROM phase_control_master
                WHERE machine_stage_id = ?
                  AND COALESCE(active, 1) = 1
                ORDER BY
                    COALESCE(phase_group_code, 'MAIN'),
                    COALESCE(display_order, 0),
                    id
                """,
                (machine_stage_id,),
            ).fetchall()

            by_key = {}
            for row in rows:
                key = (
                    PhaseTemplateManager.group_code(row["phase_group_code"]),
                    row["phase_control_key"] or PhaseTemplateManager.phase_key(row["phase_control_name"]),
                )
                by_key.setdefault(key, []).append(dict(row))

            for _, items in by_key.items():
                if len(items) <= 1:
                    continue
                keep = items[0]
                for duplicate in items[1:]:
                    cur.execute(
                        """
                        UPDATE recipe_phase_control
                        SET phase_control_id = ?
                        WHERE phase_control_id = ?
                        """,
                        (keep["id"], duplicate["id"]),
                    )
                    changed["merged"] += cur.rowcount
                    cur.execute(
                        """
                        UPDATE phase_control_master
                        SET active = 0,
                            description = COALESCE(NULLIF(description, ''), 'Deactivated duplicate phase option')
                        WHERE id = ?
                        """,
                        (duplicate["id"],),
                    )
                    changed["deactivated"] += cur.rowcount

            conn.commit()
        except Exception as exc:
            conn.rollback()
            conn.close()
            return False, [str(exc)], changed

        conn.close()
        return True, [], changed
