from database.database import get_connection
from database.plc_download_tag_readiness_manager import (
    PLCDownloadTagReadinessManager,
)
from database.stage_plc_tag_requirement_manager import (
    StagePLCTagRequirementManager,
)


class ConfigurationReadinessManager:
    REQUIRED_TAGS = [
        {
            "purpose": "RECIPE_DATA",
            "label": "CRS recipe buffer",
            "expected_type": "REAL",
            "array_required": True,
            "minimum_array_size": None,
        },
        {
            "purpose": "TEST_RECIPE_DATA",
            "label": "PLC destination buffer",
            "expected_type": "REAL",
            "array_required": True,
            "minimum_array_size": None,
        },
        {
            "purpose": "RECIPE_CODE",
            "label": "Recipe code",
            "expected_type": "STRING",
            "array_required": False,
            "minimum_array_size": None,
        },
        {
            "purpose": "DOWNLOAD_ENABLE",
            "label": "Download enable",
            "expected_type": "BOOL",
            "array_required": False,
            "minimum_array_size": None,
        },
        {
            "purpose": "MACHINE_IN_MANUAL",
            "label": "Machine manual mode",
            "expected_type": "BOOL",
            "array_required": False,
            "minimum_array_size": None,
        },
        {
            "purpose": "DOWNLOAD_REQUEST",
            "label": "Download request",
            "expected_type": "BOOL",
            "array_required": False,
            "minimum_array_size": None,
        },
        {
            "purpose": "DOWNLOAD_COMPLETE",
            "label": "Download complete",
            "expected_type": "BOOL",
            "array_required": False,
            "minimum_array_size": None,
        },
    ]

    RECOMMENDED_TAGS = [
        {
            "purpose": "DOWNLOAD_ACK",
            "label": "Download acknowledge",
            "expected_type": "BOOL",
            "array_required": False,
            "minimum_array_size": None,
        },
        {
            "purpose": "DOWNLOAD_BUSY",
            "label": "Download busy",
            "expected_type": "BOOL",
            "array_required": False,
            "minimum_array_size": None,
        },
        {
            "purpose": "DOWNLOAD_ERROR",
            "label": "Download error",
            "expected_type": "BOOL",
            "array_required": False,
            "minimum_array_size": None,
        },
        {
            "purpose": "DOWNLOAD_RESULT",
            "label": "Download result",
            "expected_type": "DINT",
            "array_required": False,
            "minimum_array_size": None,
        },
        {
            "purpose": "DOWNLOAD_OS",
            "label": "Download one-shot",
            "expected_type": "BOOL",
            "array_required": False,
            "minimum_array_size": None,
        },
        {
            "purpose": "LAST_DOWNLOAD_TIME",
            "label": "Last download time",
            "expected_type": "STRING",
            "array_required": False,
            "minimum_array_size": None,
        },
        {
            "purpose": "LAST_DOWNLOAD_USER",
            "label": "Last download user",
            "expected_type": "STRING",
            "array_required": False,
            "minimum_array_size": None,
        },
    ]

    EXPECTED_PHASE_GROUPS = {
        "FIRST_STAGE": ["APPLICATION_SIDE"],
        "SECOND_STAGE": ["CAP_STRIP_SIDE", "BT_SIDE", "SHAPING_SIDE"],
    }

    @staticmethod
    def list_stage_contexts():
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                m.id AS machine_id,
                m.machine_code,
                m.description AS machine_description,
                COALESCE(m.active, 1) AS machine_active,
                s.id AS stage_id,
                s.stage_type,
                s.description AS stage_description,
                COALESCE(s.active, 1) AS stage_active
            FROM tbm_machines m
            INNER JOIN machine_stages s
                ON s.machine_id = m.id
            ORDER BY
                m.machine_code,
                CASE UPPER(s.stage_type)
                    WHEN 'FIRST_STAGE' THEN 1
                    WHEN 'SECOND_STAGE' THEN 2
                    ELSE 99
                END,
                s.stage_type
            """
        )
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def get_stage_context(machine_id, stage_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                m.id AS machine_id,
                m.machine_code,
                m.description AS machine_description,
                COALESCE(m.active, 1) AS machine_active,
                s.id AS stage_id,
                s.stage_type,
                s.description AS stage_description,
                COALESCE(s.active, 1) AS stage_active
            FROM tbm_machines m
            INNER JOIN machine_stages s
                ON s.machine_id = m.id
            WHERE
                m.id = ?
                AND s.id = ?
            """
            ,
            (machine_id, stage_id),
        )
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def get_report(machine_id, stage_id):
        context = ConfigurationReadinessManager.get_stage_context(
            machine_id,
            stage_id,
        )
        if not context:
            return None

        tag_requirements = (
            StagePLCTagRequirementManager
            .get_stage_requirements(
                context["machine_id"],
                context["stage_id"],
                active_only=False,
            )
        )

        report = {
            "context": context,
            "sections": [],
            "tag_requirements": tag_requirements,
            "saved_plc_tags": ConfigurationReadinessManager.get_saved_plc_tags(
                context["machine_id"],
                context["stage_id"],
            ),
            "tag_purpose_options": ConfigurationReadinessManager.get_tag_purpose_options(
                tag_requirements
            ),
            "blocking_count": 0,
            "warning_count": 0,
            "ready_count": 0,
            "total_count": 0,
        }

        ConfigurationReadinessManager._add_machine_stage_section(report)
        ConfigurationReadinessManager._add_plc_registry_section(report)
        ConfigurationReadinessManager._add_parameter_section(report)
        ConfigurationReadinessManager._add_phase_section(report)
        ConfigurationReadinessManager._add_required_tag_section(report)
        ConfigurationReadinessManager._add_recommended_tag_section(report)
        ConfigurationReadinessManager._add_recipe_section(report)
        ConfigurationReadinessManager._finalize_report(report)

        return report

    @staticmethod
    def get_saved_plc_tags(machine_id, stage_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT *
            FROM plc_tags
            WHERE
                machine_id = ?
                AND stage_id = ?
            ORDER BY
                CASE WHEN COALESCE(tag_purpose, '') = '' THEN 1 ELSE 0 END,
                tag_purpose,
                tag_name
            """,
            (machine_id, stage_id),
        )
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def get_tag_purpose_options(tag_requirements=None):
        standard_purposes = [
            "RECIPE_DATA",
            "TEST_RECIPE_DATA",
            "RECIPE_CODE",
            "DOWNLOAD_ENABLE",
            "MACHINE_IN_MANUAL",
            "DOWNLOAD_REQUEST",
            "DOWNLOAD_COMPLETE",
            "DOWNLOAD_ACK",
            "DOWNLOAD_BUSY",
            "DOWNLOAD_ERROR",
            "DOWNLOAD_RESULT",
            "DOWNLOAD_OS",
            "LAST_DOWNLOAD_TIME",
            "LAST_DOWNLOAD_USER",
        ]
        for row in tag_requirements or []:
            purpose = (row.get("purpose") or "").strip().upper()
            if purpose and purpose not in standard_purposes:
                standard_purposes.append(purpose)
        return standard_purposes

    @staticmethod
    def get_all_reports():
        reports = []
        for context in ConfigurationReadinessManager.list_stage_contexts():
            report = ConfigurationReadinessManager.get_report(
                context["machine_id"],
                context["stage_id"],
            )
            if report:
                reports.append(report)
        return reports

    @staticmethod
    def _new_section(key, title, summary, severity="ok"):
        return {
            "key": key,
            "title": title,
            "summary": summary,
            "severity": severity,
            "items": [],
        }

    @staticmethod
    def _add_item(section, label, status, detail="", action=None):
        section["items"].append(
            {
                "label": label,
                "status": status,
                "detail": detail,
                "action": action,
            }
        )

    @staticmethod
    def _section_status(section):
        statuses = [item["status"] for item in section["items"]]
        if "blocked" in statuses:
            return "blocked"
        if "warning" in statuses:
            return "warning"
        return "ok"

    @staticmethod
    def _append_section(report, section):
        section["severity"] = ConfigurationReadinessManager._section_status(
            section
        )
        report["sections"].append(section)

    @staticmethod
    def _add_machine_stage_section(report):
        context = report["context"]
        section = ConfigurationReadinessManager._new_section(
            "machine_stage",
            "Machine / Stage",
            "Machine and stage records required before any template work.",
        )
        ConfigurationReadinessManager._add_item(
            section,
            "Machine",
            "ok" if context["machine_active"] else "blocked",
            f"{context['machine_code']} is active."
            if context["machine_active"]
            else f"{context['machine_code']} is disabled.",
        )
        ConfigurationReadinessManager._add_item(
            section,
            "Stage",
            "ok" if context["stage_active"] else "blocked",
            f"{context['stage_type']} is active."
            if context["stage_active"]
            else f"{context['stage_type']} is disabled.",
        )
        ConfigurationReadinessManager._append_section(report, section)

    @staticmethod
    def _add_plc_registry_section(report):
        context = report["context"]
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT *
            FROM plc_registry
            WHERE machine_stage_id = ?
            ORDER BY
                COALESCE(active, 1) DESC,
                plc_name
            """,
            (context["stage_id"],),
        )
        plcs = [dict(row) for row in cursor.fetchall()]
        conn.close()

        active_plcs = [
            plc for plc in plcs
            if int(plc.get("active", 1) or 0) == 1
        ]

        section = ConfigurationReadinessManager._new_section(
            "plc_registry",
            "PLC Registry",
            "At least one active PLC must be registered for this machine/stage.",
        )
        ConfigurationReadinessManager._add_item(
            section,
            "Active PLC",
            "ok" if active_plcs else "blocked",
            f"{len(active_plcs)} active PLC record(s)."
            if active_plcs
            else "No active PLC registered.",
        )

        if active_plcs:
            for plc in active_plcs:
                detail = f"{plc.get('plc_name')} - {plc.get('ip_address')}"
                ConfigurationReadinessManager._add_item(
                    section,
                    "PLC",
                    "ok",
                    detail,
                )

        ConfigurationReadinessManager._append_section(report, section)

    @staticmethod
    def _add_parameter_section(report):
        context = report["context"]
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
            (context["machine_id"], context["stage_id"]),
        )
        parameters = [dict(row) for row in cursor.fetchall()]
        conn.close()

        used = [
            row for row in parameters
            if int(row.get("used", 1) or 0) == 1
        ]
        invalid = []
        duplicate_tag_indexes = (
            ConfigurationReadinessManager._duplicates(used, "tag_index")
        )
        duplicate_plc_indexes = (
            ConfigurationReadinessManager._duplicates(used, "plc_array_index")
        )

        for row in used:
            tag_index = row.get("tag_index")
            plc_index = row.get("plc_array_index")
            name = (row.get("parameter_name") or "").strip()
            min_value = row.get("min_value")
            max_value = row.get("max_value")
            default_value = row.get("default_value")
            min_number = ConfigurationReadinessManager._to_float(min_value)
            max_number = ConfigurationReadinessManager._to_float(max_value)
            default_number = ConfigurationReadinessManager._to_float(
                default_value
            )

            if not name:
                invalid.append(f"Tag {tag_index}: missing parameter name")
            if tag_index is None:
                invalid.append(f"{name or 'Parameter'}: missing tag index")
            if plc_index is None:
                invalid.append(f"{name or tag_index}: missing PLC index")
            if min_value is not None and min_number is None:
                invalid.append(f"Tag {tag_index}: invalid minimum")
            if max_value is not None and max_number is None:
                invalid.append(f"Tag {tag_index}: invalid maximum")
            if default_value is not None and default_number is None:
                invalid.append(f"Tag {tag_index}: invalid default")
            if tag_index in duplicate_tag_indexes:
                invalid.append(f"Duplicate tag index {tag_index}")
            if plc_index in duplicate_plc_indexes:
                invalid.append(f"Duplicate PLC index {plc_index}")
            if (
                min_number is not None
                and max_number is not None
                and min_number > max_number
            ):
                invalid.append(f"Tag {tag_index}: min greater than max")
            if (
                default_number is not None
                and min_number is not None
                and default_number < min_number
            ):
                invalid.append(f"Tag {tag_index}: default below min")
            if (
                default_number is not None
                and max_number is not None
                and default_number > max_number
            ):
                invalid.append(f"Tag {tag_index}: default above max")

        section = ConfigurationReadinessManager._new_section(
            "parameters",
            "Parameter Template",
            "Parameter master must be present and internally valid.",
        )
        ConfigurationReadinessManager._add_item(
            section,
            "Used parameters",
            "ok" if used else "blocked",
            f"{len(used)} used parameter(s)."
            if used
            else "No used parameters configured.",
        )
        ConfigurationReadinessManager._add_item(
            section,
            "Parameter validation",
            "blocked" if invalid else "ok",
            "No duplicate index or min/max issue found."
            if not invalid
            else "; ".join(invalid[:8]),
        )
        ConfigurationReadinessManager._append_section(report, section)

    @staticmethod
    def _add_phase_section(report):
        context = report["context"]
        stage_type = (context.get("stage_type") or "").upper()
        expected_groups = (
            ConfigurationReadinessManager
            .EXPECTED_PHASE_GROUPS
            .get(stage_type, [])
        )

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT *
            FROM phase_control_group_master
            WHERE
                machine_stage_id = ?
                AND COALESCE(active, 1) = 1
            ORDER BY display_order, phase_group_name
            """,
            (context["stage_id"],),
        )
        groups = [dict(row) for row in cursor.fetchall()]
        cursor.execute(
            """
            SELECT *
            FROM phase_control_master
            WHERE
                machine_stage_id = ?
                AND COALESCE(active, 1) = 1
            ORDER BY phase_group_code, display_order, phase_control_name
            """,
            (context["stage_id"],),
        )
        options = [dict(row) for row in cursor.fetchall()]
        conn.close()

        configured_group_codes = {
            (group.get("phase_group_code") or "").upper()
            for group in groups
        }
        missing_groups = [
            code for code in expected_groups
            if code not in configured_group_codes
        ]
        option_group_codes = {
            (option.get("phase_group_code") or "").upper()
            for option in options
        }
        missing_options = [
            code for code in expected_groups
            if code not in option_group_codes
        ]
        missing_empty = []
        for code in expected_groups:
            if not any(
                (option.get("phase_group_code") or "").upper() == code
                and
                (option.get("phase_control_name") or "").strip().upper()
                == "EMPTY PHASE"
                for option in options
            ):
                missing_empty.append(code)

        section = ConfigurationReadinessManager._new_section(
            "phase_master",
            "Phase Control Master",
            "Stage-specific phase groups and selectable phases.",
        )
        ConfigurationReadinessManager._add_item(
            section,
            "Phase groups",
            "blocked" if missing_groups else "ok",
            f"{len(groups)} group(s) configured."
            if not missing_groups
            else "Missing: " + ", ".join(missing_groups),
        )
        ConfigurationReadinessManager._add_item(
            section,
            "Phase options",
            "blocked" if missing_options else "ok",
            f"{len(options)} phase option(s) configured."
            if not missing_options
            else "No options in: " + ", ".join(missing_options),
        )
        ConfigurationReadinessManager._add_item(
            section,
            "Empty phase",
            "blocked" if missing_empty else "ok",
            "Empty Phase is available in required groups."
            if not missing_empty
            else "Missing Empty Phase in: " + ", ".join(missing_empty),
        )
        ConfigurationReadinessManager._append_section(report, section)

    @staticmethod
    def _add_required_tag_section(report):
        context = report["context"]
        required_tags = (
            StagePLCTagRequirementManager
            .get_stage_requirements(
                context["machine_id"],
                context["stage_id"],
                requirement_level=StagePLCTagRequirementManager.LEVEL_REQUIRED,
                active_only=True,
            )
        )
        section = ConfigurationReadinessManager._build_tag_section(
            report,
            key="required_tags",
            title="Required PLC Tags",
            summary="Tags needed for restore, save, upload, download, and safety gates. Rules are editable per machine/stage.",
            required_tags=required_tags,
            missing_status="blocked",
        )
        ConfigurationReadinessManager._append_section(report, section)

    @staticmethod
    def _add_recommended_tag_section(report):
        context = report["context"]
        recommended_tags = (
            StagePLCTagRequirementManager
            .get_stage_requirements(
                context["machine_id"],
                context["stage_id"],
                requirement_level=StagePLCTagRequirementManager.LEVEL_RECOMMENDED,
                active_only=True,
            )
        )
        section = ConfigurationReadinessManager._build_tag_section(
            report,
            key="recommended_tags",
            title="Recommended PLC Tags",
            summary="Handshake and history tags recommended before plant deployment. Rules are editable per machine/stage.",
            required_tags=recommended_tags,
            missing_status="warning",
        )
        ConfigurationReadinessManager._append_section(report, section)

    @staticmethod
    def _build_tag_section(report, key, title, summary, required_tags, missing_status):
        context = report["context"]
        tags = PLCDownloadTagReadinessManager.get_tags_for_stage(
            machine_id=context["machine_id"],
            stage_id=context["stage_id"],
        )
        section = ConfigurationReadinessManager._new_section(
            key,
            title,
            summary,
        )
        for required in required_tags:
            tag = PLCDownloadTagReadinessManager.find_tag_for_purpose(
                tags,
                required["purpose"],
            )
            item = {
                "purpose": required["purpose"],
                "label": required["label"],
                "expected_type": required.get("expected_type"),
                "array_required": bool(required.get("array_required")),
                "minimum_array_size": required.get("minimum_array_size"),
                "array_start_index": required.get("array_start_index"),
                "array_end_index": required.get("array_end_index"),
                "default_tag_name": required.get("default_tag_name"),
                "search_hint": required.get("search_hint"),
                "configured": tag is not None,
                "ready": True,
                "tag": tag,
                "issues": [],
            }

            if not tag:
                status = missing_status
                detail = f"{required['purpose']} is not mapped."
            else:
                PLCDownloadTagReadinessManager.validate_tag(
                    item=item,
                    tag=tag,
                    required=required,
                )
                status = "ok" if item["ready"] else "blocked"
                tag_name = tag.get("tag_name")
                tag_type = tag.get("tag_type") or "-"
                detail = (
                    f"{tag_name} ({tag_type})"
                    if item["ready"]
                    else f"{tag_name}: " + "; ".join(item["issues"])
                )

            ConfigurationReadinessManager._add_item(
                section,
                required["label"],
                status,
                detail,
                action=required["purpose"],
            )
        return section

    @staticmethod
    def _add_recipe_section(report):
        context = report["context"]
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total_count,
                SUM(CASE WHEN UPPER(COALESCE(status, '')) = 'DRAFT' THEN 1 ELSE 0 END) AS draft_count,
                SUM(CASE WHEN UPPER(COALESCE(status, '')) = 'REVIEW' THEN 1 ELSE 0 END) AS review_count,
                SUM(CASE WHEN UPPER(COALESCE(status, '')) = 'RELEASED' THEN 1 ELSE 0 END) AS released_count
            FROM recipes
            WHERE
                machine_id = ?
                AND stage_id = ?
                AND COALESCE(is_test_only, 0) = 0
            """,
            (context["machine_id"], context["stage_id"]),
        )
        row = dict(cursor.fetchone())

        cursor.execute(
            """
            SELECT COUNT(*) AS current_count
            FROM recipes r
            WHERE
                r.machine_id = ?
                AND r.stage_id = ?
                AND COALESCE(r.is_test_only, 0) = 0
                AND UPPER(COALESCE(r.status, '')) = 'RELEASED'
                AND r.version = (
                    SELECT MAX(r2.version)
                    FROM recipes r2
                    WHERE
                        r2.machine_id = r.machine_id
                        AND r2.stage_id = r.stage_id
                        AND UPPER(r2.recipe_code) = UPPER(r.recipe_code)
                        AND COALESCE(r2.is_test_only, 0) = 0
                        AND UPPER(COALESCE(r2.status, '')) = 'RELEASED'
                )
            """,
            (context["machine_id"], context["stage_id"]),
        )
        current_row = dict(cursor.fetchone())
        conn.close()

        section = ConfigurationReadinessManager._new_section(
            "recipes",
            "Recipe Records",
            "Recipes can be created after the template and phase master are ready.",
        )
        total_count = int(row.get("total_count") or 0)
        current_count = int(current_row.get("current_count") or 0)
        released_count = int(row.get("released_count") or 0)
        draft_count = int(row.get("draft_count") or 0)

        ConfigurationReadinessManager._add_item(
            section,
            "Recipe records",
            "ok" if total_count else "warning",
            f"{total_count} recipe(s), {draft_count} draft, {released_count} released.",
        )
        ConfigurationReadinessManager._add_item(
            section,
            "Current production recipe",
            "ok" if current_count else "warning",
            f"{current_count} current released recipe(s)."
            if current_count
            else "No current released recipe yet.",
        )
        ConfigurationReadinessManager._append_section(report, section)

    @staticmethod
    def _duplicates(rows, key):
        seen = set()
        duplicates = set()
        for row in rows:
            value = row.get(key)
            if value is None:
                continue
            if value in seen:
                duplicates.add(value)
            seen.add(value)
        return duplicates

    @staticmethod
    def _to_float(value):
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _finalize_report(report):
        for section in report["sections"]:
            for item in section["items"]:
                report["total_count"] += 1
                if item["status"] == "blocked":
                    report["blocking_count"] += 1
                elif item["status"] == "warning":
                    report["warning_count"] += 1
                else:
                    report["ready_count"] += 1

        if report["blocking_count"]:
            report["status"] = "BLOCKED"
            report["status_class"] = "blocked"
        elif report["warning_count"]:
            report["status"] = "READY WITH WARNINGS"
            report["status_class"] = "warning"
        else:
            report["status"] = "READY"
            report["status_class"] = "ready"

        if report["total_count"]:
            report["score"] = int(
                round(
                    (report["ready_count"] / report["total_count"]) * 100
                )
            )
        else:
            report["score"] = 0
