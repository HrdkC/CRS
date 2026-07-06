import re

from database.database import get_connection
from database.audit_manager import AuditManager


class PLC1DArrayRecipeBuilder:
    """
    Build P15/any stage parameter master + draft recipe from a PLC 1D array.

    Safety:
    - Creates DRAFT recipe only.
    - Does not release recipe.
    - Does not write to PLC.
    - Refuses to create parameter master if the stage already has definitions.
    """

    @staticmethod
    def _row_to_dict(row):
        if row is None:
            return None
        if isinstance(row, dict):
            return row
        try:
            return dict(row)
        except Exception:
            # Fallback for tuple rows should normally not be needed because
            # database.get_connection() uses sqlite3.Row in CRS.
            return None

    @staticmethod
    def get_machine_stage_context(machine_id, stage_id):
        conn = get_connection()
        cur = conn.cursor()
        row = cur.execute(
            """
            SELECT
                m.id AS machine_id,
                m.machine_code,
                s.id AS stage_id,
                s.stage_type,
                f.family_name
            FROM machine_stages s
            INNER JOIN tbm_machines m ON m.id = s.machine_id
            LEFT JOIN tbm_families f ON f.id = m.family_id
            WHERE m.id = ? AND s.id = ?
            """,
            (machine_id, stage_id),
        ).fetchone()
        conn.close()
        return PLC1DArrayRecipeBuilder._row_to_dict(row)

    @staticmethod
    def get_machine_stage_context_by_plc_id(plc_id):
        conn = get_connection()
        cur = conn.cursor()
        row = cur.execute(
            """
            SELECT
                p.id AS plc_id,
                p.plc_name,
                p.ip_address,
                m.id AS machine_id,
                m.machine_code,
                s.id AS stage_id,
                s.stage_type,
                f.family_name
            FROM plc_registry p
            INNER JOIN machine_stages s ON s.id = p.machine_stage_id
            INNER JOIN tbm_machines m ON m.id = s.machine_id
            LEFT JOIN tbm_families f ON f.id = m.family_id
            WHERE p.id = ?
            """,
            (plc_id,),
        ).fetchone()
        conn.close()
        return PLC1DArrayRecipeBuilder._row_to_dict(row)

    @staticmethod
    def get_active_plc(machine_id, stage_id):
        conn = get_connection()
        cur = conn.cursor()
        row = cur.execute(
            """
            SELECT p.*, m.machine_code, s.stage_type
            FROM plc_registry p
            INNER JOIN machine_stages s ON s.id = p.machine_stage_id
            INNER JOIN tbm_machines m ON m.id = s.machine_id
            WHERE s.id = ? AND s.machine_id = ? AND p.active = 1
            ORDER BY p.id DESC
            LIMIT 1
            """,
            (stage_id, machine_id),
        ).fetchone()
        conn.close()
        return PLC1DArrayRecipeBuilder._row_to_dict(row)

    @staticmethod
    def count_parameter_definitions(machine_id, stage_id):
        conn = get_connection()
        cur = conn.cursor()
        row = cur.execute(
            """
            SELECT COUNT(*) AS c
            FROM parameter_definitions
            WHERE machine_id = ? AND stage_id = ?
            """,
            (machine_id, stage_id),
        ).fetchone()
        conn.close()
        return int(row["c"] if row else 0)

    @staticmethod
    def count_stage_recipes(machine_id, stage_id):
        conn = get_connection()
        cur = conn.cursor()
        row = cur.execute(
            """
            SELECT COUNT(*) AS c
            FROM recipes
            WHERE machine_id = ? AND stage_id = ?
            """,
            (machine_id, stage_id),
        ).fetchone()
        conn.close()
        return int(row["c"] if row else 0)

    @staticmethod
    def _normalize_array_tag_name(tag_name):
        """Accept CRS_Recipe_Data or CRS_Recipe_Data[0], but return the base array tag."""
        cleaned = str(tag_name or "").strip()
        cleaned = re.sub(r"\{\d+\}\s*$", "", cleaned).strip()
        match = re.match(r"^(.+?)\[(\d+)\]\s*$", cleaned)
        if match:
            return match.group(1).strip()
        return cleaned

    @staticmethod
    def _reject_known_non_array_tag(tag_name):
        non_array_tags = {
            "CRS_RECIPE_CODE": "STRING",
            "CRS_DOWNLOAD_ENABLE": "BOOL",
            "CRS_TEST_MACHINE_IN_MANUAL": "BOOL",
            "CRS_DOWNLOAD_REQUEST": "BOOL",
            "CRS_DOWNLOAD_COMPLETE": "BOOL",
            "CRS_DOWNLOAD_ACK": "BOOL",
            "CRS_DOWNLOAD_BUSY": "BOOL",
            "CRS_DOWNLOAD_ERROR": "BOOL",
            "CRS_DOWNLOAD_RESULT": "DINT",
        }
        key = str(tag_name or "").strip().upper()
        datatype = non_array_tags.get(key)
        if datatype:
            return (
                f"{tag_name} is {datatype}, not a 1D recipe array. "
                "Use CRS_Recipe_Data or CRS_Test_Recipe_Data for PLC array preview/import."
            )
        return None

    @staticmethod
    def _parameter_name_prefix(machine_id, stage_id):
        context = PLC1DArrayRecipeBuilder.get_machine_stage_context(machine_id, stage_id)
        if context:
            machine_code = str(context.get("machine_code") or "PLC").upper()
            stage_type = str(context.get("stage_type") or "STAGE").upper()
            if stage_type == "FIRST_STAGE":
                return f"{machine_code} FS Param"
            if stage_type == "SECOND_STAGE":
                return f"{machine_code} SS Param"
            return f"{machine_code} Param"
        return "PLC Param"

    @staticmethod
    def _stage_array_limit(machine_id, stage_id):
        context = PLC1DArrayRecipeBuilder.get_machine_stage_context(machine_id, stage_id)
        if not context:
            return None
        machine_code = str(context.get("machine_code") or "").upper()
        stage_type = str(context.get("stage_type") or "").upper()
        if machine_code == "P15" and stage_type == "SECOND_STAGE":
            return 150
        return None

    @staticmethod
    def _tag_metadata_summary(tag_metadata):
        if not isinstance(tag_metadata, dict):
            return "metadata unavailable"

        summary_parts = []
        for key in ("data_type", "tag_type", "array", "dimensions", "dim", "type"):
            if key in tag_metadata:
                summary_parts.append(f"{key}={tag_metadata.get(key)!r}")
        return ", ".join(summary_parts) if summary_parts else str(tag_metadata)[:250]

    @staticmethod
    def _find_controller_tag_match(plc_conn, requested_tag_name):
        """
        Return (resolved_tag_name, metadata, similar_tags).
        Uses the online controller tag list when pycomm3 tag initialization is enabled.
        """
        tags = getattr(plc_conn, "tags", {}) or {}
        if requested_tag_name in tags:
            return requested_tag_name, tags.get(requested_tag_name), []

        requested_upper = requested_tag_name.upper()
        for online_name, metadata in tags.items():
            if str(online_name).upper() == requested_upper:
                return online_name, metadata, []

        requested_tokens = [token for token in requested_upper.split("_") if token]
        similar = []
        for online_name in tags.keys():
            online_upper = str(online_name).upper()
            if online_upper.startswith("CRS_") or all(token in online_upper for token in requested_tokens[:2]):
                similar.append(str(online_name))
            if len(similar) >= 12:
                break
        return None, None, similar

    @staticmethod
    def _read_single_expression(plc_conn, expression):
        response = plc_conn.read(expression)
        error = getattr(response, "error", None)
        if error:
            raise RuntimeError(str(error))
        return getattr(response, "value", None)

    @staticmethod
    def _read_tag_block(plc_conn, tag_name, start_index, count, diagnostics=None):
        """
        Robust Logix array read.

        Some PLC/pycomm3 combinations accept TAG[0]{150}; some are more reliable
        with TAG{150} for a zero-based full array read. This method tries both
        patterns and then falls back to per-index reads.
        """
        diagnostics = diagnostics if isinstance(diagnostics, list) else []
        tag_name = tag_name.strip()

        attempts = []
        if start_index == 0:
            attempts.append(f"{tag_name}{{{count}}}")
        attempts.append(f"{tag_name}[{start_index}]{{{count}}}")

        block_errors = []
        for expression in attempts:
            try:
                value = PLC1DArrayRecipeBuilder._read_single_expression(plc_conn, expression)
                if isinstance(value, (list, tuple)):
                    values = list(value)
                    if len(values) >= count:
                        diagnostics.append(f"PLC array read used expression: {expression}")
                        return values[:count], None
                    raise RuntimeError(f"Returned {len(values)} value(s), expected {count}.")
                if count == 1:
                    diagnostics.append(f"PLC single-value read used expression: {expression}")
                    return [value], None
                raise RuntimeError(f"Returned non-list value: {value!r}")
            except Exception as ex:
                block_errors.append(f"{expression}: {ex}")

        values = []
        index_errors = []
        for index in range(start_index, start_index + count):
            expression = f"{tag_name}[{index}]"
            try:
                value = PLC1DArrayRecipeBuilder._read_single_expression(plc_conn, expression)
                values.append(value)
            except Exception as ex:
                index_errors.append(f"{expression}: {ex}")
                values.append(None)

        if index_errors and all(value is None for value in values):
            return values, (
                f"Block read failed: {block_errors[:3]}; "
                f"per-index read failed: {index_errors[:5]}"
            )

        if index_errors:
            diagnostics.append("PLC array read used per-index fallback.")
            return values, f"Some indexes failed: {index_errors[:5]}"

        diagnostics.append("PLC array read used per-index fallback.")
        return values, None

    @staticmethod
    def read_array_values(machine_id, stage_id, tag_name, start_index, end_index):
        result = {
            "ok": False,
            "plc": None,
            "tag_name": tag_name,
            "start_index": start_index,
            "end_index": end_index,
            "count": 0,
            "values": [],
            "errors": [],
            "warnings": [],
            "diagnostics": [],
        }

        if not tag_name or not str(tag_name).strip():
            result["errors"].append("PLC array tag name is required.")
            return result

        tag_name = PLC1DArrayRecipeBuilder._normalize_array_tag_name(tag_name)
        result["tag_name"] = tag_name

        non_array_error = PLC1DArrayRecipeBuilder._reject_known_non_array_tag(tag_name)
        if non_array_error:
            result["errors"].append(non_array_error)
            return result

        try:
            start_index = int(start_index)
            end_index = int(end_index)
        except Exception:
            result["errors"].append("Start index and end index must be numbers.")
            return result

        if start_index < 0 or end_index < start_index:
            result["errors"].append("Invalid array index range.")
            return result

        count = end_index - start_index + 1
        if count > 1000:
            result["errors"].append("For safety, V1 allows maximum 1000 array elements per import.")
            return result

        stage_limit = PLC1DArrayRecipeBuilder._stage_array_limit(machine_id, stage_id)
        if stage_limit and (start_index >= stage_limit or end_index >= stage_limit):
            result["errors"].append(
                f"Selected stage recipe array limit is REAL[{stage_limit}], so valid indexes are 0 to {stage_limit - 1}."
            )
            return result

        plc = PLC1DArrayRecipeBuilder.get_active_plc(machine_id, stage_id)
        result["plc"] = plc
        result["count"] = count

        if not plc:
            result["errors"].append("No active PLC registered for this machine/stage.")
            return result

        try:
            try:
                from pycomm3 import LogixDriver
            except Exception as import_ex:
                result["errors"].append(f"pycomm3 is not installed or not available: {import_ex}")
                return result

            with LogixDriver(plc["ip_address"], init_tags=True, init_program_tags=False, timeout=10) as plc_conn:
                result["diagnostics"].append(
                    f"Connected to active PLC {plc.get('plc_name')} at {plc.get('ip_address')}."
                )

                resolved_tag_name, tag_metadata, similar_tags = PLC1DArrayRecipeBuilder._find_controller_tag_match(
                    plc_conn,
                    tag_name,
                )
                if not resolved_tag_name:
                    message = (
                        f"{tag_name} was not found in the online controller tag list for active PLC "
                        f"{plc.get('plc_name')} ({plc.get('ip_address')})."
                    )
                    if similar_tags:
                        message += f" Similar CRS tags found online: {', '.join(similar_tags)}."
                    else:
                        message += " No CRS_ controller tags were found in the online browse list."
                    result["errors"].append(message)
                    return result

                if resolved_tag_name != tag_name:
                    result["warnings"].append(
                        f"Using online tag name {resolved_tag_name} instead of entered name {tag_name}."
                    )
                    tag_name = resolved_tag_name
                    result["tag_name"] = resolved_tag_name

                result["diagnostics"].append(
                    f"Online controller tag found: {resolved_tag_name} ({PLC1DArrayRecipeBuilder._tag_metadata_summary(tag_metadata)})."
                )

                values, warning = PLC1DArrayRecipeBuilder._read_tag_block(
                    plc_conn=plc_conn,
                    tag_name=tag_name,
                    start_index=start_index,
                    count=count,
                    diagnostics=result["diagnostics"],
                )
            if warning:
                if values and all(value is None for value in values):
                    result["errors"].append(
                        "PLC array read failed for all selected indexes. "
                        f"The tag was found in the active PLC online tag list, but read failed. "
                        f"Check External Access is not None, the tag is a controller-scope REAL array, "
                        f"and the selected indexes exist. Detail: {warning}"
                    )
                    return result
                result["warnings"].append(warning)
            rows = []
            parameter_prefix = PLC1DArrayRecipeBuilder._parameter_name_prefix(machine_id, stage_id)
            for offset, value in enumerate(values):
                index = start_index + offset
                rows.append({
                    "index": index,
                    "value": value,
                    "parameter_name": f"{parameter_prefix} {index:03d}",
                })
            result["values"] = rows
            result["ok"] = True
        except Exception as ex:
            result["errors"].append(f"PLC array read failed: {ex}")

        return result

    @staticmethod
    def _safe_float(value, fallback=0.0):
        try:
            if value is None:
                return fallback
            if isinstance(value, bool):
                return 1.0 if value else 0.0
            return float(value)
        except Exception:
            return fallback

    @staticmethod
    def _get_columns(cur, table_name):
        return {row["name"] for row in cur.execute(f"PRAGMA table_info({table_name})").fetchall()}

    @staticmethod
    def _insert_recipe_phase_rows(cur, recipe_id, stage_id):
        phase_columns = PLC1DArrayRecipeBuilder._get_columns(cur, "recipe_phase_control")
        master_columns = PLC1DArrayRecipeBuilder._get_columns(cur, "phase_control_master")

        if "machine_stage_id" in master_columns and "phase_group_code" in master_columns:
            phase_rows = cur.execute(
                """
                SELECT id, phase_group_code, phase_group_name, display_order, phase_control_name
                FROM phase_control_master
                WHERE
                    machine_stage_id = ?
                    AND stage_type = 'SECOND_STAGE'
                    AND active = 1
                    AND phase_group_code IN ('CAP_STRIP_SIDE', 'BT_SIDE')
                ORDER BY
                    CASE phase_group_code
                        WHEN 'CAP_STRIP_SIDE' THEN 1
                        WHEN 'BT_SIDE' THEN 2
                        ELSE 99
                    END,
                    display_order,
                    id
                """,
                (stage_id,),
            ).fetchall()
        else:
            phase_rows = []

        if not phase_rows:
            raise RuntimeError(
                "P15 Second Stage phase-control masters not found. "
                "Run upgrade_p15_second_stage_phase_master.py first."
            )

        for phase in phase_rows:
            line_no = int(phase["display_order"] or 0)
            columns = [
                "recipe_id",
                "line_no",
                "phase_control_id",
                "stop_option",
                "position_option",
                "sequence_no",
            ]
            values = [
                recipe_id,
                line_no,
                phase["id"],
                None,
                None,
                line_no,
            ]

            if "phase_group_code" in phase_columns:
                columns.append("phase_group_code")
                values.append(phase["phase_group_code"])
            if "phase_group_name" in phase_columns:
                columns.append("phase_group_name")
                values.append(phase["phase_group_name"])
            if "used" in phase_columns:
                columns.append("used")
                values.append(1)

            placeholders = ", ".join(["?"] * len(values))
            cur.execute(
                f"""
                INSERT INTO recipe_phase_control ({', '.join(columns)})
                VALUES ({placeholders})
                """,
                tuple(values),
            )

        return len(phase_rows)

    @staticmethod
    def build_from_plc_array(
        machine_id,
        stage_id,
        tag_name,
        start_index,
        end_index,
        recipe_code,
        recipe_name,
        version=1,
        username="system",
        role="SYSTEM",
        reason=None,
        unit="",
        min_value=0.0,
        max_value=999999.0,
        datatype="REAL",
        dry_run=True,
    ):
        result = PLC1DArrayRecipeBuilder.read_array_values(
            machine_id=machine_id,
            stage_id=stage_id,
            tag_name=tag_name,
            start_index=start_index,
            end_index=end_index,
        )
        result.update({
            "dry_run": dry_run,
            "created": False,
            "recipe_id": None,
            "parameter_count": 0,
            "phase_count": 0,
        })

        if not result["ok"]:
            return result

        recipe_code = (recipe_code or "").strip().upper()
        recipe_name = (recipe_name or "").strip()
        reason = (reason or "").strip()

        if not recipe_code:
            result["errors"].append("Recipe code is required.")
            result["ok"] = False
            return result
        if not recipe_name:
            result["errors"].append("Recipe name is required.")
            result["ok"] = False
            return result
        if not dry_run and len(reason) < 8:
            result["errors"].append("Reason is required for actual import/build.")
            result["ok"] = False
            return result

        existing_params = PLC1DArrayRecipeBuilder.count_parameter_definitions(machine_id, stage_id)
        if dry_run:
            result["parameter_count"] = len(result["values"])
            result["warnings"].append("Dry run only. No DB rows were created.")
            if existing_params > 0:
                result["warnings"].append(
                    "Parameter master already exists for this machine/stage. Preview is allowed, but Build will not overwrite it."
                )
            return result

        if existing_params > 0:
            result["errors"].append(
                f"Parameter master already exists for machine_id={machine_id}, stage_id={stage_id}. "
                "Build is blocked because CRS will not overwrite existing parameter definitions."
            )
            result["ok"] = False
            return result

        conn = get_connection()
        try:
            cur = conn.cursor()

            duplicate = cur.execute(
                """
                SELECT id
                FROM recipes
                WHERE machine_id = ? AND stage_id = ?
                  AND UPPER(recipe_code) = UPPER(?) AND version = ?
                """,
                (machine_id, stage_id, recipe_code, int(version)),
            ).fetchone()
            if duplicate:
                raise RuntimeError(f"Recipe {recipe_code} version {version} already exists for this stage.")

            cur.execute(
                """
                INSERT INTO recipes
                    (machine_id, stage_id, recipe_code, recipe_name, version, status, created_by)
                VALUES
                    (?, ?, ?, ?, ?, 'DRAFT', ?)
                """,
                (machine_id, stage_id, recipe_code, recipe_name, int(version), username),
            )
            recipe_id = cur.lastrowid

            parameter_count = 0
            for row in result["values"]:
                idx = int(row["index"])
                value = PLC1DArrayRecipeBuilder._safe_float(row["value"], 0.0)
                parameter_name = f"{PLC1DArrayRecipeBuilder._parameter_name_prefix(machine_id, stage_id)} {idx:03d}"

                cur.execute(
                    """
                    INSERT INTO parameter_definitions
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
                    VALUES (?, ?, ?, ?, ?, '', ?, ?, ?, ?, ?, ?, 1, ?)
                    """,
                    (
                        machine_id,
                        stage_id,
                        idx,
                        idx,
                        parameter_name,
                        unit,
                        PLC1DArrayRecipeBuilder._safe_float(min_value, 0.0),
                        PLC1DArrayRecipeBuilder._safe_float(max_value, 999999.0),
                        value,
                        datatype,
                        f"Imported from PLC 1D array {tag_name}[{idx}] - rename before release",
                        username,
                    ),
                )
                parameter_definition_id = cur.lastrowid

                cur.execute(
                    """
                    INSERT INTO recipe_parameter_values
                        (recipe_id, parameter_definition_id, parameter_value, is_modified)
                    VALUES (?, ?, ?, 0)
                    """,
                    (recipe_id, parameter_definition_id, value),
                )
                parameter_count += 1

            phase_count = PLC1DArrayRecipeBuilder._insert_recipe_phase_rows(
                cur=cur,
                recipe_id=recipe_id,
                stage_id=stage_id,
            )

            conn.commit()

            AuditManager.log_event(
                username=username,
                role=role,
                action="P15_SECOND_STAGE_RECIPE_IMPORTED_FROM_PLC_ARRAY",
                change_source="PLC_1D_ARRAY_IMPORT",
                plc_name=result["plc"]["plc_name"] if result.get("plc") else None,
                recipe_code=recipe_code,
                recipe_version=int(version),
                record_id=recipe_id,
                old_value="P15 SECOND_STAGE parameter_count=0",
                new_value=(
                    f"recipe_id={recipe_id}; tag={tag_name}; "
                    f"indexes={start_index}-{end_index}; parameters={parameter_count}; "
                    f"phase_rows={phase_count}; status=DRAFT"
                ),
                reason=reason,
            )

            result["created"] = True
            result["recipe_id"] = recipe_id
            result["parameter_count"] = parameter_count
            result["phase_count"] = phase_count
            result["warnings"].append(
                "Draft recipe created. Rename placeholder parameters and set engineering limits before release."
            )
            return result

        except Exception as ex:
            conn.rollback()
            result["ok"] = False
            result["errors"].append(str(ex))
            return result
        finally:
            conn.close()
