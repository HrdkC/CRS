from database.database import get_connection


class StagePLCTagRequirementManager:
    """Editable per-machine/stage PLC tag validation rules.

    Purpose names remain standard so existing PLC tag mapping continues to work,
    but every stage can define its own expected tag name, datatype, array size,
    and required/recommended status.
    """

    LEVEL_REQUIRED = "REQUIRED"
    LEVEL_RECOMMENDED = "RECOMMENDED"

    GENERIC_PHASE_PURPOSES = {
        "PHASE_CONTROL_STRING",
        "PHASE_STOP_STRING",
        "PHASE_POSITION_STRING",
    }

    SECOND_STAGE_PHASE_PURPOSES = {
        "CAP_STRIP_PHASE_CONTROL_STRING",
        "CAP_STRIP_PHASE_STOP_STRING",
        "BT_PHASE_CONTROL_STRING",
        "BT_PHASE_STOP_STRING",
        "BT_PHASE_POSITION_STRING",
    }

    DEFAULT_RULES = [
        {
            "purpose": "RECIPE_DATA",
            "label": "CRS recipe buffer",
            "requirement_level": LEVEL_REQUIRED,
            "expected_type": "REAL",
            "array_required": 1,
            "minimum_array_size": None,
            "array_start_index": None,
            "array_end_index": None,
            "default_tag_name": "CRS_Recipe_Data",
            "search_hint": "CRS_Recipe_Data",
            "active": 1,
            "display_order": 10,
        },
        {
            "purpose": "TEST_RECIPE_DATA",
            "label": "PLC destination buffer",
            "requirement_level": LEVEL_REQUIRED,
            "expected_type": "REAL",
            "array_required": 1,
            "minimum_array_size": None,
            "array_start_index": None,
            "array_end_index": None,
            "default_tag_name": "CRS_Test_Recipe_Data",
            "search_hint": "CRS_Test_Recipe_Data",
            "active": 1,
            "display_order": 20,
        },
        {
            "purpose": "RECIPE_CODE",
            "label": "Recipe code",
            "requirement_level": LEVEL_REQUIRED,
            "expected_type": "STRING",
            "array_required": 0,
            "minimum_array_size": None,
            "array_start_index": None,
            "array_end_index": None,
            "default_tag_name": "CRS_Recipe_Code",
            "search_hint": "CRS_Recipe_Code",
            "active": 1,
            "display_order": 30,
        },
        {
            "purpose": "DOWNLOAD_ENABLE",
            "label": "Download enable",
            "requirement_level": LEVEL_REQUIRED,
            "expected_type": "BOOL",
            "array_required": 0,
            "minimum_array_size": None,
            "array_start_index": None,
            "array_end_index": None,
            "default_tag_name": "CRS_Download_Enable",
            "search_hint": "Download_Enable",
            "active": 1,
            "display_order": 40,
        },
        {
            "purpose": "MACHINE_IN_MANUAL",
            "label": "Machine manual mode",
            "requirement_level": LEVEL_REQUIRED,
            "expected_type": "BOOL",
            "array_required": 0,
            "minimum_array_size": None,
            "array_start_index": None,
            "array_end_index": None,
            "default_tag_name": "CRS_Test_Machine_In_Manual",
            "search_hint": "Manual",
            "active": 1,
            "display_order": 50,
        },
        {
            "purpose": "DOWNLOAD_REQUEST",
            "label": "Download request",
            "requirement_level": LEVEL_REQUIRED,
            "expected_type": "BOOL",
            "array_required": 0,
            "minimum_array_size": None,
            "array_start_index": None,
            "array_end_index": None,
            "default_tag_name": "CRS_Download_Request",
            "search_hint": "Download_Request",
            "active": 1,
            "display_order": 60,
        },
        {
            "purpose": "DOWNLOAD_COMPLETE",
            "label": "Download complete",
            "requirement_level": LEVEL_REQUIRED,
            "expected_type": "BOOL",
            "array_required": 0,
            "minimum_array_size": None,
            "array_start_index": None,
            "array_end_index": None,
            "default_tag_name": "CRS_Download_Complete",
            "search_hint": "Download_Complete",
            "active": 1,
            "display_order": 70,
        },
        {
            "purpose": "PHASE_CONTROL_STRING",
            "label": "Phase control names",
            "requirement_level": LEVEL_REQUIRED,
            "expected_type": "STRING",
            "array_required": 1,
            "minimum_array_size": None,
            "array_start_index": None,
            "array_end_index": None,
            "default_tag_name": "CRS_Phase_Cntrl_String",
            "search_hint": "Phase_Cntrl_String",
            "active": 1,
            "display_order": 80,
        },
        {
            "purpose": "PHASE_STOP_STRING",
            "label": "Phase stop options",
            "requirement_level": LEVEL_REQUIRED,
            "expected_type": "STRING",
            "array_required": 1,
            "minimum_array_size": None,
            "array_start_index": None,
            "array_end_index": None,
            "default_tag_name": "CRS_Phase_Cntrl_Stop_String",
            "search_hint": "Phase_Cntrl_Stop",
            "active": 1,
            "display_order": 90,
        },
        {
            "purpose": "PHASE_POSITION_STRING",
            "label": "Phase position options",
            "requirement_level": LEVEL_REQUIRED,
            "expected_type": "STRING",
            "array_required": 1,
            "minimum_array_size": None,
            "array_start_index": None,
            "array_end_index": None,
            "default_tag_name": "CRS_Phase_Cntrl_Position_String",
            "search_hint": "Phase_Cntrl_Position",
            "active": 1,
            "display_order": 100,
        },
        {
            "purpose": "CAP_STRIP_PHASE_CONTROL_STRING",
            "label": "Cap strip phase names",
            "requirement_level": LEVEL_REQUIRED,
            "expected_type": "STRING",
            "array_required": 1,
            "minimum_array_size": 2,
            "array_start_index": 0,
            "array_end_index": 1,
            "default_tag_name": "CRS_Phase_Cntrl_String_CapSd",
            "search_hint": "Phase_Cntrl_String_CapSd",
            "active": 1,
            "display_order": 82,
        },
        {
            "purpose": "CAP_STRIP_PHASE_STOP_STRING",
            "label": "Cap strip stop options",
            "requirement_level": LEVEL_REQUIRED,
            "expected_type": "STRING",
            "array_required": 1,
            "minimum_array_size": 2,
            "array_start_index": 0,
            "array_end_index": 1,
            "default_tag_name": "CRS_Phase_Cntrl_Stop_String_CapSd",
            "search_hint": "Phase_Cntrl_Stop_String_CapSd",
            "active": 1,
            "display_order": 84,
        },
        {
            "purpose": "BT_PHASE_CONTROL_STRING",
            "label": "B&T phase names",
            "requirement_level": LEVEL_REQUIRED,
            "expected_type": "STRING",
            "array_required": 1,
            "minimum_array_size": 20,
            "array_start_index": 0,
            "array_end_index": 19,
            "default_tag_name": "CRS_Phase_Cntrl_String",
            "search_hint": "Phase_Cntrl_String",
            "active": 1,
            "display_order": 86,
        },
        {
            "purpose": "BT_PHASE_STOP_STRING",
            "label": "B&T stop options",
            "requirement_level": LEVEL_REQUIRED,
            "expected_type": "STRING",
            "array_required": 1,
            "minimum_array_size": 10,
            "array_start_index": 0,
            "array_end_index": 9,
            "default_tag_name": "CRS_Phase_Cntrl_Stop_String",
            "search_hint": "Phase_Cntrl_Stop_String",
            "active": 1,
            "display_order": 88,
        },
        {
            "purpose": "BT_PHASE_POSITION_STRING",
            "label": "B&T position options",
            "requirement_level": LEVEL_REQUIRED,
            "expected_type": "STRING",
            "array_required": 1,
            "minimum_array_size": 10,
            "array_start_index": 0,
            "array_end_index": 9,
            "default_tag_name": "CRS_Phase_Cntrl_Pos_String",
            "search_hint": "Phase_Cntrl_Pos_String",
            "active": 1,
            "display_order": 90,
        },
        {
            "purpose": "DOWNLOAD_ACK",
            "label": "Download acknowledge",
            "requirement_level": LEVEL_RECOMMENDED,
            "expected_type": "BOOL",
            "array_required": 0,
            "minimum_array_size": None,
            "array_start_index": None,
            "array_end_index": None,
            "default_tag_name": "CRS_Download_Ack",
            "search_hint": "Download_Ack",
            "active": 1,
            "display_order": 110,
        },
        {
            "purpose": "DOWNLOAD_BUSY",
            "label": "Download busy",
            "requirement_level": LEVEL_RECOMMENDED,
            "expected_type": "BOOL",
            "array_required": 0,
            "minimum_array_size": None,
            "array_start_index": None,
            "array_end_index": None,
            "default_tag_name": "CRS_Download_Busy",
            "search_hint": "Download_Busy",
            "active": 1,
            "display_order": 120,
        },
        {
            "purpose": "DOWNLOAD_ERROR",
            "label": "Download error",
            "requirement_level": LEVEL_RECOMMENDED,
            "expected_type": "BOOL",
            "array_required": 0,
            "minimum_array_size": None,
            "array_start_index": None,
            "array_end_index": None,
            "default_tag_name": "CRS_Download_Error",
            "search_hint": "Download_Error",
            "active": 1,
            "display_order": 130,
        },
        {
            "purpose": "DOWNLOAD_RESULT",
            "label": "Download result",
            "requirement_level": LEVEL_RECOMMENDED,
            "expected_type": "DINT",
            "array_required": 0,
            "minimum_array_size": None,
            "array_start_index": None,
            "array_end_index": None,
            "default_tag_name": "CRS_Download_Result",
            "search_hint": "Download_Result",
            "active": 1,
            "display_order": 140,
        },
        {
            "purpose": "DOWNLOAD_OS",
            "label": "Download one-shot",
            "requirement_level": LEVEL_RECOMMENDED,
            "expected_type": "BOOL",
            "array_required": 0,
            "minimum_array_size": None,
            "array_start_index": None,
            "array_end_index": None,
            "default_tag_name": "CRS_Download_OS",
            "search_hint": "Download_OS",
            "active": 1,
            "display_order": 150,
        },
        {
            "purpose": "LAST_DOWNLOAD_TIME",
            "label": "Last download time",
            "requirement_level": LEVEL_RECOMMENDED,
            "expected_type": "STRING",
            "array_required": 0,
            "minimum_array_size": None,
            "array_start_index": None,
            "array_end_index": None,
            "default_tag_name": "CRS_Last_Download_Time",
            "search_hint": "Last_Download_Time",
            "active": 1,
            "display_order": 160,
        },
        {
            "purpose": "LAST_DOWNLOAD_USER",
            "label": "Last download user",
            "requirement_level": LEVEL_RECOMMENDED,
            "expected_type": "STRING",
            "array_required": 0,
            "minimum_array_size": None,
            "array_start_index": None,
            "array_end_index": None,
            "default_tag_name": "CRS_Last_Download_User",
            "search_hint": "Last_Download_User",
            "active": 1,
            "display_order": 170,
        },
    ]

    @staticmethod
    def ensure_table():
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS stage_plc_tag_requirements
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id INTEGER NOT NULL,
                stage_id INTEGER NOT NULL,
                purpose TEXT NOT NULL,
                label TEXT NOT NULL,
                requirement_level TEXT NOT NULL DEFAULT 'REQUIRED',
                expected_type TEXT,
                array_required INTEGER NOT NULL DEFAULT 0,
                minimum_array_size INTEGER,
                array_start_index INTEGER,
                array_end_index INTEGER,
                default_tag_name TEXT,
                search_hint TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                display_order INTEGER NOT NULL DEFAULT 100,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(machine_id, stage_id, purpose)
            )
            """
        )
        conn.commit()
        conn.close()

    @staticmethod
    def _get_stage_type(cur, machine_id, stage_id):
        row = cur.execute(
            """
            SELECT s.stage_type
            FROM machine_stages s
            WHERE s.id = ?
            """,
            (stage_id,),
        ).fetchone()
        return (row["stage_type"] if row else "") or ""

    @staticmethod
    def _default_rule_for_stage(rule, stage_type):
        updated = dict(rule)
        stage = str(stage_type or "").strip().upper()
        purpose = str(updated.get("purpose") or "").strip().upper()
        if purpose in StagePLCTagRequirementManager.GENERIC_PHASE_PURPOSES:
            if stage == "FIRST_STAGE":
                updated["minimum_array_size"] = 12
                updated["array_start_index"] = 0
                updated["array_end_index"] = 11
            elif stage == "SECOND_STAGE":
                updated["active"] = 0
        elif purpose in StagePLCTagRequirementManager.SECOND_STAGE_PHASE_PURPOSES:
            if stage != "SECOND_STAGE":
                updated["active"] = 0
        return updated

    @staticmethod
    def seed_stage_defaults(machine_id, stage_id):
        StagePLCTagRequirementManager.ensure_table()
        conn = get_connection()
        cur = conn.cursor()
        stage_type = StagePLCTagRequirementManager._get_stage_type(cur, machine_id, stage_id)
        for default_rule in StagePLCTagRequirementManager.DEFAULT_RULES:
            rule = StagePLCTagRequirementManager._default_rule_for_stage(default_rule, stage_type)
            purpose = str(rule["purpose"] or "").strip().upper()
            cur.execute(
                """
                INSERT OR IGNORE INTO stage_plc_tag_requirements
                (machine_id, stage_id, purpose, label, requirement_level, expected_type,
                 array_required, minimum_array_size, array_start_index, array_end_index,
                 default_tag_name, search_hint, active, display_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    machine_id,
                    stage_id,
                    rule["purpose"],
                    rule["label"],
                    rule["requirement_level"],
                    rule["expected_type"],
                    int(rule["array_required"] or 0),
                    rule.get("minimum_array_size"),
                    rule.get("array_start_index"),
                    rule.get("array_end_index"),
                    rule.get("default_tag_name"),
                    rule.get("search_hint"),
                    int(rule.get("active", 1) or 0),
                    int(rule.get("display_order", 100) or 100),
                ),
            )
            if (
                purpose in StagePLCTagRequirementManager.GENERIC_PHASE_PURPOSES
                or purpose in StagePLCTagRequirementManager.SECOND_STAGE_PHASE_PURPOSES
            ):
                cur.execute(
                    """
                    UPDATE stage_plc_tag_requirements
                    SET
                        minimum_array_size = COALESCE(minimum_array_size, ?),
                        array_start_index = COALESCE(array_start_index, ?),
                        array_end_index = COALESCE(array_end_index, ?),
                        active = CASE WHEN ? = 0 THEN 0 ELSE active END,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE
                        machine_id = ?
                        AND stage_id = ?
                        AND purpose = ?
                    """,
                    (
                        rule.get("minimum_array_size"),
                        rule.get("array_start_index"),
                        rule.get("array_end_index"),
                        int(rule.get("active", 1) or 0),
                        machine_id,
                        stage_id,
                        rule["purpose"],
                    ),
                )
        conn.commit()
        conn.close()

    @staticmethod
    def get_stage_requirements(machine_id, stage_id, requirement_level=None, active_only=True):
        StagePLCTagRequirementManager.seed_stage_defaults(machine_id, stage_id)
        conn = get_connection()
        cur = conn.cursor()
        conditions = ["machine_id = ?", "stage_id = ?"]
        params = [machine_id, stage_id]
        if requirement_level:
            conditions.append("UPPER(requirement_level) = UPPER(?)")
            params.append(requirement_level)
        if active_only:
            conditions.append("COALESCE(active, 1) = 1")
        cur.execute(
            f"""
            SELECT *
            FROM stage_plc_tag_requirements
            WHERE {' AND '.join(conditions)}
            ORDER BY
                CASE UPPER(requirement_level)
                    WHEN 'REQUIRED' THEN 1
                    WHEN 'RECOMMENDED' THEN 2
                    ELSE 3
                END,
                display_order,
                purpose
            """,
            tuple(params),
        )
        rows = [dict(row) for row in cur.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def get_stage_requirement(machine_id, stage_id, purpose):
        StagePLCTagRequirementManager.seed_stage_defaults(machine_id, stage_id)
        conn = get_connection()
        cur = conn.cursor()
        row = cur.execute(
            """
            SELECT *
            FROM stage_plc_tag_requirements
            WHERE machine_id = ? AND stage_id = ? AND UPPER(purpose) = UPPER(?)
            """,
            (machine_id, stage_id, purpose),
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def get_payload_size(machine_id, stage_id, purpose="RECIPE_DATA", default=None):
        rule = StagePLCTagRequirementManager.get_stage_requirement(machine_id, stage_id, purpose)
        try:
            size = int(rule.get("minimum_array_size") if rule else 0)
        except Exception:
            size = 0
        return size if size > 0 else default

    @staticmethod
    def _to_int_or_none(value):
        if value in (None, ""):
            return None
        try:
            return int(float(value))
        except Exception:
            return None

    @staticmethod
    def _clean_rule(row):
        purpose = str(row.get("purpose") or "").strip().upper()
        label = str(row.get("label") or purpose).strip()
        requirement_level = str(row.get("requirement_level") or "REQUIRED").strip().upper()
        if requirement_level not in {"REQUIRED", "RECOMMENDED"}:
            requirement_level = "REQUIRED"
        expected_type = str(row.get("expected_type") or "").strip().upper()
        array_required = 1 if str(row.get("array_required") or "0").strip().lower() in {"1", "true", "yes", "on"} else 0
        minimum_array_size = StagePLCTagRequirementManager._to_int_or_none(row.get("minimum_array_size"))
        array_start_index = StagePLCTagRequirementManager._to_int_or_none(row.get("array_start_index"))
        array_end_index = StagePLCTagRequirementManager._to_int_or_none(row.get("array_end_index"))
        if array_required and minimum_array_size and array_start_index is None:
            array_start_index = 0
        if array_required and minimum_array_size and array_end_index is None:
            array_end_index = (array_start_index or 0) + minimum_array_size - 1
        return {
            "purpose": purpose,
            "label": label,
            "requirement_level": requirement_level,
            "expected_type": expected_type,
            "array_required": array_required,
            "minimum_array_size": minimum_array_size if array_required else None,
            "array_start_index": array_start_index if array_required else None,
            "array_end_index": array_end_index if array_required else None,
            "default_tag_name": str(row.get("default_tag_name") or "").strip(),
            "search_hint": str(row.get("search_hint") or "").strip(),
            "active": 1 if str(row.get("active") or "0").strip().lower() in {"1", "true", "yes", "on"} else 0,
            "display_order": StagePLCTagRequirementManager._to_int_or_none(row.get("display_order")) or 100,
        }

    @staticmethod
    def validate_rules(rows):
        errors = []
        purposes = set()
        for idx, raw in enumerate(rows, start=1):
            row = StagePLCTagRequirementManager._clean_rule(raw)
            purpose = row["purpose"]
            if not purpose:
                errors.append(f"Row {idx}: purpose is required.")
                continue
            if purpose in purposes:
                errors.append(f"Row {idx}: duplicate purpose {purpose}.")
            purposes.add(purpose)
            if not row["label"]:
                errors.append(f"{purpose}: label is required.")
            if row["array_required"]:
                size = row.get("minimum_array_size")
                start = row.get("array_start_index")
                end = row.get("array_end_index")
                if not size or size <= 0:
                    errors.append(f"{purpose}: minimum array size must be greater than zero.")
                if start is None or end is None:
                    errors.append(f"{purpose}: start and end indexes are required for array tags.")
                elif start > end:
                    errors.append(f"{purpose}: start index cannot be greater than end index.")
                elif size and (end - start + 1) < size:
                    errors.append(f"{purpose}: index span must cover minimum array size {size}.")
        return errors

    @staticmethod
    def save_stage_requirements(machine_id, stage_id, rows):
        StagePLCTagRequirementManager.seed_stage_defaults(machine_id, stage_id)
        errors = StagePLCTagRequirementManager.validate_rules(rows)
        if errors:
            return False, errors
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute("BEGIN")
            for raw in rows:
                row = StagePLCTagRequirementManager._clean_rule(raw)
                cur.execute(
                    """
                    INSERT INTO stage_plc_tag_requirements
                    (machine_id, stage_id, purpose, label, requirement_level, expected_type,
                     array_required, minimum_array_size, array_start_index, array_end_index,
                     default_tag_name, search_hint, active, display_order)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(machine_id, stage_id, purpose) DO UPDATE SET
                        label = excluded.label,
                        requirement_level = excluded.requirement_level,
                        expected_type = excluded.expected_type,
                        array_required = excluded.array_required,
                        minimum_array_size = excluded.minimum_array_size,
                        array_start_index = excluded.array_start_index,
                        array_end_index = excluded.array_end_index,
                        default_tag_name = excluded.default_tag_name,
                        search_hint = excluded.search_hint,
                        active = excluded.active,
                        display_order = excluded.display_order,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        machine_id,
                        stage_id,
                        row["purpose"],
                        row["label"],
                        row["requirement_level"],
                        row["expected_type"],
                        row["array_required"],
                        row["minimum_array_size"],
                        row["array_start_index"],
                        row["array_end_index"],
                        row["default_tag_name"],
                        row["search_hint"],
                        row["active"],
                        row["display_order"],
                    ),
                )
            conn.commit()
        except Exception as exc:
            conn.rollback()
            conn.close()
            return False, [str(exc)]
        conn.close()
        return True, []
