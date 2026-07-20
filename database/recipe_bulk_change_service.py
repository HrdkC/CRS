import uuid

from database.audit_manager import AuditManager
from database.database import transaction
from database.recipe_parameter_audit_manager import RecipeParameterAuditManager


class RecipeBulkChangeService:
    DETAIL_FIELDS = (
        "parameter_name",
        "unit",
        "min_value",
        "max_value",
        "default_value",
        "used",
    )

    @staticmethod
    def apply(
        recipe_id,
        changes,
        changed_by,
        user_role,
        change_reason,
        can_edit_details=False,
        client_ip=None,
        workstation_name=None,
    ):
        reason = (change_reason or "").strip()
        if not reason:
            return {"success": False, "message": "Change reason is required."}

        correlation_id = uuid.uuid4().hex
        changed_count = 0
        detail_changed_count = 0

        try:
            with transaction(immediate=True) as conn:
                cursor = conn.cursor()
                recipe = cursor.execute(
                    """
                    SELECT r.*,
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
                    FROM recipes r WHERE r.id=?
                    """,
                    (int(recipe_id),),
                ).fetchone()
                if not recipe:
                    raise ValueError("Recipe not found.")
                if recipe["status"] == "RELEASED" and int(recipe["is_current_released"] or 0) != 1:
                    raise ValueError("Historical released recipe is read-only.")

                for change in changes:
                    value_id = int(change["value_id"])
                    row = cursor.execute(
                        """
                        SELECT rpv.*, pd.parameter_name, pd.unit, pd.min_value,
                               pd.max_value, pd.default_value, pd.used, pd.tag_index
                        FROM recipe_parameter_values rpv
                        JOIN parameter_definitions pd ON pd.id=rpv.parameter_definition_id
                        WHERE rpv.id=? AND rpv.recipe_id=?
                        """,
                        (value_id, int(recipe_id)),
                    ).fetchone()
                    if not row:
                        raise ValueError(f"Recipe value {value_id} does not belong to recipe {recipe_id}.")

                    if can_edit_details:
                        detail_updates = {}
                        for field in RecipeBulkChangeService.DETAIL_FIELDS:
                            new_value = change.get(field)
                            old_value = row[field]
                            if str(old_value if old_value is not None else "") != str(
                                new_value if new_value is not None else ""
                            ):
                                detail_updates[field] = (old_value, new_value)

                        if detail_updates:
                            assignments = ", ".join(f"{field}=?" for field in detail_updates)
                            params = [item[1] for item in detail_updates.values()]
                            params.append(int(row["parameter_definition_id"]))
                            cursor.execute(
                                f"UPDATE parameter_definitions SET {assignments}, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                                params,
                            )
                            for field, (old_value, new_value) in detail_updates.items():
                                AuditManager.log_event(
                                    username=changed_by,
                                    role=user_role,
                                    action="RECIPE_PARAMETER_DETAIL_CHANGED",
                                    change_source="BULK_RECIPE_PARAMETER_EDIT",
                                    recipe_code=recipe["recipe_code"],
                                    recipe_version=recipe["version"],
                                    record_id=row["parameter_definition_id"],
                                    parameter_name=change.get("parameter_name") or row["parameter_name"],
                                    old_value=f"{field}: {old_value}",
                                    new_value=f"{field}: {new_value}",
                                    reason=reason,
                                    client_ip=client_ip,
                                    workstation_name=workstation_name,
                                    correlation_id=correlation_id,
                                    _connection=conn,
                                )
                                detail_changed_count += 1

                    old_value = row["parameter_value"]
                    new_value = float(change["value"])
                    if old_value is not None and float(old_value) == new_value:
                        continue

                    cursor.execute(
                        """
                        UPDATE recipe_parameter_values
                        SET parameter_value=?, is_modified=1, updated_at=CURRENT_TIMESTAMP
                        WHERE id=?
                        """,
                        (new_value, value_id),
                    )
                    source = (
                        "CURRENT_RELEASED_BULK_EDIT"
                        if recipe["status"] == "RELEASED"
                        else "DRAFT_RECIPE_BULK_EDIT"
                    )
                    parameter_name = change.get("parameter_name") or row["parameter_name"]
                    RecipeParameterAuditManager.log_change(
                        recipe_id=recipe_id,
                        recipe_parameter_value_id=value_id,
                        parameter_definition_id=row["parameter_definition_id"],
                        old_value=old_value,
                        new_value=new_value,
                        changed_by=changed_by,
                        recipe_code=recipe["recipe_code"],
                        recipe_version=recipe["version"],
                        parameter_name=parameter_name,
                        tag_index=row["tag_index"],
                        change_source=source,
                        change_reason=reason,
                        user_role=user_role,
                        client_ip=client_ip,
                        workstation_name=workstation_name,
                        correlation_id=correlation_id,
                        _connection=conn,
                    )
                    AuditManager.log_event(
                        username=changed_by,
                        role=user_role,
                        action="RECIPE_PARAMETER_CHANGED",
                        change_source=source,
                        recipe_code=recipe["recipe_code"],
                        recipe_version=recipe["version"],
                        record_id=value_id,
                        parameter_name=parameter_name,
                        old_value=str(old_value),
                        new_value=str(new_value),
                        reason=reason,
                        client_ip=client_ip,
                        workstation_name=workstation_name,
                        correlation_id=correlation_id,
                        _connection=conn,
                    )
                    changed_count += 1

                AuditManager.log_event(
                    username=changed_by,
                    role=user_role,
                    action="RECIPE_BULK_EDIT_COMPLETED",
                    change_source="BULK_RECIPE_PARAMETER_EDIT",
                    recipe_code=recipe["recipe_code"],
                    recipe_version=recipe["version"],
                    record_id=recipe_id,
                    new_value=(
                        f"value_changes={changed_count}; detail_changes={detail_changed_count}"
                    ),
                    reason=reason,
                    client_ip=client_ip,
                    workstation_name=workstation_name,
                    correlation_id=correlation_id,
                    _connection=conn,
                )

            return {
                "success": True,
                "changed_count": changed_count,
                "detail_changed_count": detail_changed_count,
                "correlation_id": correlation_id,
            }
        except Exception as exc:
            return {
                "success": False,
                "message": "Bulk edit failed and all changes were rolled back.",
                "error_type": type(exc).__name__,
                "correlation_id": correlation_id,
            }
