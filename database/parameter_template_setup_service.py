"""Guided, transactional parameter-template setup for configured PLC arrays."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from typing import Any, Iterable

from database.audit_manager import AuditManager
from database.database import get_connection, transaction


_NUMERIC_ARRAY_TYPES = {"REAL", "DINT", "INT", "SINT"}
_RECOMMENDED_PURPOSE_ORDER = {
    "RECIPE_DATA": 0,
    "TEST_RECIPE_DATA": 1,
}


class ParameterTemplateSetupError(ValueError):
    """Raised for user-correctable template setup problems."""


@dataclass(frozen=True)
class TemplateSetupResult:
    created_count: int
    skipped_count: int
    backfilled_value_count: int
    source_tag_name: str
    start_index: int
    end_index: int
    correlation_id: str


@dataclass(frozen=True)
class TemplateBulkUpdateResult:
    changed_count: int
    backfilled_value_count: int
    correlation_id: str


def _clean_text(value: Any, *, max_length: int = 200) -> str:
    text = str(value or "").strip()
    return text[:max_length]


def _as_int(value: Any, label: str) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ParameterTemplateSetupError(f"{label} must be a whole number.") from exc


def _as_float(value: Any, label: str) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ParameterTemplateSetupError(f"{label} must be a valid number.") from exc


def _as_used(value: Any) -> int:
    if isinstance(value, bool):
        return 1 if value else 0
    return 1 if str(value).strip().lower() in {"1", "true", "yes", "on"} else 0


def _validate_reason(reason: Any) -> str:
    cleaned = _clean_text(reason, max_length=500)
    if len(cleaned) < 8:
        raise ParameterTemplateSetupError(
            "Change reason is required and must contain at least 8 characters."
        )
    return cleaned


def _source_tag_bounds(tag: dict[str, Any]) -> tuple[int, int]:
    start = tag.get("array_start_index")
    end = tag.get("array_end_index")
    size = tag.get("array_size")

    try:
        start_value = int(start) if start is not None else 0
    except (TypeError, ValueError):
        start_value = 0

    if end is not None:
        try:
            end_value = int(end)
        except (TypeError, ValueError):
            end_value = start_value
    elif size is not None:
        try:
            end_value = start_value + max(0, int(size) - 1)
        except (TypeError, ValueError):
            end_value = start_value
    else:
        end_value = start_value

    return start_value, max(start_value, end_value)


class ParameterTemplateSetupService:
    """Build and maintain parameter definitions without PLC reads or writes."""

    @staticmethod
    def get_configured_array_tags(machine_id: int, stage_id: int) -> list[dict[str, Any]]:
        conn = get_connection()
        try:
            rows = conn.execute(
                """
                SELECT
                    id,
                    tag_name,
                    UPPER(COALESCE(tag_type, '')) AS tag_type,
                    COALESCE(is_array, 0) AS is_array,
                    array_size,
                    array_start_index,
                    array_end_index,
                    UPPER(COALESCE(tag_purpose, '')) AS tag_purpose,
                    COALESCE(description, '') AS description
                FROM plc_tags
                WHERE machine_id = ? AND stage_id = ?
                  AND COALESCE(is_array, 0) = 1
                  AND UPPER(COALESCE(tag_type, '')) IN ('REAL', 'DINT', 'INT', 'SINT')
                ORDER BY
                    CASE UPPER(COALESCE(tag_purpose, ''))
                        WHEN 'RECIPE_DATA' THEN 0
                        WHEN 'TEST_RECIPE_DATA' THEN 1
                        ELSE 2
                    END,
                    UPPER(tag_name)
                """,
                (int(machine_id), int(stage_id)),
            ).fetchall()
        finally:
            conn.close()

        tags: list[dict[str, Any]] = []
        for raw in rows:
            tag = dict(raw)
            start_index, end_index = _source_tag_bounds(tag)
            tag["array_start_index"] = start_index
            tag["array_end_index"] = end_index
            tag["effective_count"] = end_index - start_index + 1
            tag["recommended"] = tag.get("tag_purpose") == "RECIPE_DATA"
            tags.append(tag)
        return tags

    @staticmethod
    def create_missing_from_configured_array(
        *,
        machine_id: int,
        stage_id: int,
        source_tag_id: Any,
        start_index: Any,
        end_index: Any,
        name_prefix: Any,
        unit: Any,
        min_value: Any,
        max_value: Any,
        default_value: Any,
        username: str,
        role: str,
        reason: Any,
        request_metadata: dict[str, Any] | None = None,
    ) -> TemplateSetupResult:
        source_tag_id_value = _as_int(source_tag_id, "Configured PLC array")
        start_value = _as_int(start_index, "Start index")
        end_value = _as_int(end_index, "End index")
        min_number = _as_float(min_value, "Minimum value")
        max_number = _as_float(max_value, "Maximum value")
        default_number = _as_float(default_value, "Default value")
        reason_text = _validate_reason(reason)
        prefix = _clean_text(name_prefix, max_length=80)
        unit_text = _clean_text(unit, max_length=30)

        if len(prefix) < 3:
            raise ParameterTemplateSetupError(
                "Parameter name prefix must contain at least 3 characters."
            )
        if end_value < start_value:
            raise ParameterTemplateSetupError(
                "End index cannot be lower than start index."
            )
        row_count = end_value - start_value + 1
        if row_count > 1000:
            raise ParameterTemplateSetupError(
                "A maximum of 1000 parameter rows can be created in one action."
            )
        if max_number < min_number:
            raise ParameterTemplateSetupError(
                "Maximum value cannot be lower than minimum value."
            )
        if default_number < min_number or default_number > max_number:
            raise ParameterTemplateSetupError(
                "Default value must be within the selected minimum and maximum limits."
            )

        metadata = request_metadata or {}
        correlation_id = str(uuid.uuid4())

        with transaction(immediate=True) as conn:
            tag_row = conn.execute(
                """
                SELECT *
                FROM plc_tags
                WHERE id = ? AND machine_id = ? AND stage_id = ?
                """,
                (source_tag_id_value, int(machine_id), int(stage_id)),
            ).fetchone()
            if not tag_row:
                raise ParameterTemplateSetupError(
                    "The selected PLC tag is not configured for this machine/stage."
                )

            source_tag = dict(tag_row)
            tag_type = str(source_tag.get("tag_type") or "").strip().upper()
            if int(source_tag.get("is_array") or 0) != 1 or tag_type not in _NUMERIC_ARRAY_TYPES:
                raise ParameterTemplateSetupError(
                    "Select a configured numeric PLC array tag (REAL, DINT, INT, or SINT)."
                )

            configured_start, configured_end = _source_tag_bounds(source_tag)
            if start_value < configured_start or end_value > configured_end:
                raise ParameterTemplateSetupError(
                    f"Used range must remain inside configured tag range "
                    f"{configured_start} to {configured_end}."
                )

            existing_rows = conn.execute(
                """
                SELECT id, tag_index, plc_array_index, parameter_name
                FROM parameter_definitions
                WHERE machine_id = ? AND stage_id = ?
                """,
                (int(machine_id), int(stage_id)),
            ).fetchall()
            existing_tag_indexes = {int(row["tag_index"]) for row in existing_rows}
            existing_plc_indexes = {
                int(row["plc_array_index"])
                for row in existing_rows
                if row["plc_array_index"] is not None
            }
            existing_names = {
                str(row["parameter_name"] or "").strip().casefold()
                for row in existing_rows
            }

            created_ids: list[int] = []
            skipped_count = 0
            for array_index in range(start_value, end_value + 1):
                # Existing template rows are preserved. The wizard only fills gaps.
                if array_index in existing_tag_indexes or array_index in existing_plc_indexes:
                    skipped_count += 1
                    continue

                parameter_name = f"{prefix} {array_index:03d}".strip()
                base_name = parameter_name
                suffix = 2
                while parameter_name.casefold() in existing_names:
                    parameter_name = f"{base_name} ({suffix})"
                    suffix += 1
                existing_names.add(parameter_name.casefold())

                cursor = conn.execute(
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
                        int(machine_id),
                        int(stage_id),
                        array_index,
                        array_index,
                        parameter_name,
                        unit_text,
                        min_number,
                        max_number,
                        default_number,
                        tag_type,
                        (
                            f"Guided template row for {source_tag['tag_name']}"
                            f"[{array_index}]. Rename and confirm engineering limits before release."
                        ),
                        username,
                    ),
                )
                created_ids.append(int(cursor.lastrowid))

            backfilled_count = 0
            for parameter_id in created_ids:
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO recipe_parameter_values
                        (recipe_id, parameter_definition_id, parameter_value, is_modified)
                    SELECT id, ?, ?, 0
                    FROM recipes
                    WHERE machine_id = ? AND stage_id = ?
                    """,
                    (
                        parameter_id,
                        default_number,
                        int(machine_id),
                        int(stage_id),
                    ),
                )
                backfilled_count += max(0, int(cursor.rowcount or 0))

            AuditManager.log_event(
                username=username,
                role=role,
                action="PARAMETER_TEMPLATE_GUIDED_SETUP",
                change_source="PARAMETER_TEMPLATE_WIZARD",
                record_id=int(stage_id),
                old_value=f"existing_rows={len(existing_rows)}",
                new_value=(
                    f"source_tag={source_tag['tag_name']}; range={start_value}-{end_value}; "
                    f"created={len(created_ids)}; skipped={skipped_count}; "
                    f"backfilled_recipe_values={backfilled_count}"
                ),
                reason=reason_text,
                user_agent=metadata.get("user_agent"),
                forwarded_for=metadata.get("forwarded_for"),
                request_host=metadata.get("request_host"),
                correlation_id=correlation_id,
                _connection=conn,
            )

        return TemplateSetupResult(
            created_count=len(created_ids),
            skipped_count=skipped_count,
            backfilled_value_count=backfilled_count,
            source_tag_name=str(source_tag["tag_name"]),
            start_index=start_value,
            end_index=end_value,
            correlation_id=correlation_id,
        )

    @staticmethod
    def bulk_update_template(
        *,
        machine_id: int,
        stage_id: int,
        changes: Iterable[dict[str, Any]],
        username: str,
        role: str,
        reason: Any,
        request_metadata: dict[str, Any] | None = None,
    ) -> TemplateBulkUpdateResult:
        reason_text = _validate_reason(reason)
        submitted = list(changes or [])
        if not submitted:
            raise ParameterTemplateSetupError(
                "No parameter changes were detected. Edit at least one row before saving."
            )
        if len(submitted) > 1000:
            raise ParameterTemplateSetupError(
                "A maximum of 1000 changed parameter rows can be saved in one action."
            )

        parsed: dict[int, dict[str, Any]] = {}
        for raw in submitted:
            parameter_id = _as_int(raw.get("id"), "Parameter row")
            if parameter_id in parsed:
                raise ParameterTemplateSetupError(
                    f"Parameter row {parameter_id} was submitted more than once."
                )
            name = _clean_text(raw.get("parameter_name"), max_length=160)
            if not name:
                raise ParameterTemplateSetupError("Parameter name cannot be blank.")
            unit_text = _clean_text(raw.get("unit"), max_length=30)
            min_number = _as_float(raw.get("min_value"), f"Minimum for {name}")
            max_number = _as_float(raw.get("max_value"), f"Maximum for {name}")
            default_number = _as_float(raw.get("default_value"), f"Default for {name}")
            if max_number < min_number:
                raise ParameterTemplateSetupError(
                    f"{name}: maximum value cannot be lower than minimum value."
                )
            if default_number < min_number or default_number > max_number:
                raise ParameterTemplateSetupError(
                    f"{name}: default value must remain inside minimum and maximum limits."
                )
            parsed[parameter_id] = {
                "parameter_name": name,
                "unit": unit_text,
                "min_value": min_number,
                "max_value": max_number,
                "default_value": default_number,
                "used": _as_used(raw.get("used")),
            }

        metadata = request_metadata or {}
        correlation_id = str(uuid.uuid4())
        changed_count = 0
        backfilled_count = 0

        with transaction(immediate=True) as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM parameter_definitions
                WHERE machine_id = ? AND stage_id = ?
                ORDER BY tag_index, id
                """,
                (int(machine_id), int(stage_id)),
            ).fetchall()
            current_by_id = {int(row["id"]): dict(row) for row in rows}

            missing_ids = sorted(set(parsed) - set(current_by_id))
            if missing_ids:
                raise ParameterTemplateSetupError(
                    "One or more parameter rows no longer belong to this machine/stage. Refresh and try again."
                )

            final_name_owner: dict[str, int] = {}
            for parameter_id, current in current_by_id.items():
                final_name = (
                    parsed.get(parameter_id, {}).get("parameter_name")
                    or str(current.get("parameter_name") or "").strip()
                )
                normalized = final_name.casefold()
                prior = final_name_owner.get(normalized)
                if prior is not None and prior != parameter_id:
                    raise ParameterTemplateSetupError(
                        f"Parameter name '{final_name}' is duplicated. Names must be unique for the stage."
                    )
                final_name_owner[normalized] = parameter_id

            for parameter_id, new_values in parsed.items():
                old = current_by_id[parameter_id]
                old_values = {
                    "parameter_name": str(old.get("parameter_name") or "").strip(),
                    "unit": str(old.get("unit") or "").strip(),
                    "min_value": float(old.get("min_value") or 0.0),
                    "max_value": float(old.get("max_value") or 0.0),
                    "default_value": float(old.get("default_value") or 0.0),
                    "used": int(old.get("used") if old.get("used") is not None else 1),
                }
                if old_values == new_values:
                    continue

                conn.execute(
                    """
                    UPDATE parameter_definitions
                    SET parameter_name = ?, unit = ?, min_value = ?, max_value = ?,
                        default_value = ?, used = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND machine_id = ? AND stage_id = ?
                    """,
                    (
                        new_values["parameter_name"],
                        new_values["unit"],
                        new_values["min_value"],
                        new_values["max_value"],
                        new_values["default_value"],
                        new_values["used"],
                        parameter_id,
                        int(machine_id),
                        int(stage_id),
                    ),
                )

                if old_values["used"] == 0 and new_values["used"] == 1:
                    cursor = conn.execute(
                        """
                        INSERT OR IGNORE INTO recipe_parameter_values
                            (recipe_id, parameter_definition_id, parameter_value, is_modified)
                        SELECT id, ?, ?, 0
                        FROM recipes
                        WHERE machine_id = ? AND stage_id = ?
                        """,
                        (
                            parameter_id,
                            new_values["default_value"],
                            int(machine_id),
                            int(stage_id),
                        ),
                    )
                    backfilled_count += max(0, int(cursor.rowcount or 0))

                AuditManager.log_event(
                    username=username,
                    role=role,
                    action="PARAMETER_TEMPLATE_ROW_UPDATED",
                    change_source="PARAMETER_TEMPLATE_BULK_EDIT",
                    record_id=parameter_id,
                    parameter_name=new_values["parameter_name"],
                    old_value=json.dumps(old_values, sort_keys=True),
                    new_value=json.dumps(new_values, sort_keys=True),
                    reason=reason_text,
                    user_agent=metadata.get("user_agent"),
                    forwarded_for=metadata.get("forwarded_for"),
                    request_host=metadata.get("request_host"),
                    correlation_id=correlation_id,
                    _connection=conn,
                )
                changed_count += 1

            if changed_count == 0:
                raise ParameterTemplateSetupError(
                    "No actual parameter changes were found."
                )

            AuditManager.log_event(
                username=username,
                role=role,
                action="PARAMETER_TEMPLATE_BULK_UPDATE_COMPLETED",
                change_source="PARAMETER_TEMPLATE_BULK_EDIT",
                record_id=int(stage_id),
                old_value=None,
                new_value=(
                    f"changed_rows={changed_count}; "
                    f"backfilled_recipe_values={backfilled_count}"
                ),
                reason=reason_text,
                user_agent=metadata.get("user_agent"),
                forwarded_for=metadata.get("forwarded_for"),
                request_host=metadata.get("request_host"),
                correlation_id=correlation_id,
                _connection=conn,
            )

        return TemplateBulkUpdateResult(
            changed_count=changed_count,
            backfilled_value_count=backfilled_count,
            correlation_id=correlation_id,
        )
