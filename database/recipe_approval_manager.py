import uuid

from database.audit_manager import AuditManager
from database.database import transaction
from database.recipe_status_history_manager import RecipeStatusHistoryManager


class RecipeApprovalManager:
    ALLOWED = {
        "DRAFT": {"REVIEW"},
        "REVIEW": {"APPROVED", "DRAFT"},
        "APPROVED": {"RELEASED"},
        "RELEASED": set(),
    }

    @staticmethod
    def submit_for_review(recipe_id, username, remarks=""):
        return RecipeApprovalManager.change_status(
            recipe_id, "REVIEW", username, remarks
        )

    @staticmethod
    def approve_recipe(recipe_id, username, remarks=""):
        return RecipeApprovalManager.change_status(
            recipe_id, "APPROVED", username, remarks
        )

    @staticmethod
    def reject_recipe(recipe_id, username, remarks):
        if not (remarks or "").strip():
            return False, "Rejection Remarks Required"
        return RecipeApprovalManager.change_status(
            recipe_id, "DRAFT", username, remarks
        )

    @staticmethod
    def change_status(recipe_id, new_status, username, remarks=""):
        new_status = str(new_status or "").upper()
        remarks = (remarks or "").strip()
        correlation_id = uuid.uuid4().hex
        try:
            with transaction(immediate=True) as conn:
                cursor = conn.cursor()
                recipe = cursor.execute(
                    "SELECT * FROM recipes WHERE id=?", (int(recipe_id),)
                ).fetchone()
                if not recipe:
                    return False, "Recipe Not Found"

                old_status = str(recipe["status"] or "").upper()
                if new_status not in RecipeApprovalManager.ALLOWED.get(old_status, set()):
                    return False, f"Invalid Workflow : {old_status} -> {new_status}"

                if new_status == "APPROVED":
                    current = cursor.execute(
                        """
                        SELECT MAX(version) AS current_version
                        FROM recipes
                        WHERE machine_id=? AND stage_id=?
                          AND UPPER(recipe_code)=UPPER(?)
                          AND status='RELEASED'
                        """,
                        (
                            recipe["machine_id"], recipe["stage_id"],
                            recipe["recipe_code"],
                        ),
                    ).fetchone()
                    if (
                        current
                        and current["current_version"] is not None
                        and int(current["current_version"]) >= int(recipe["version"])
                    ):
                        return (
                            False,
                            f"Cannot approve V{recipe['version']} because "
                            f"V{current['current_version']} is already released.",
                        )

                cursor.execute(
                    "UPDATE recipes SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    (new_status, int(recipe_id)),
                )
                RecipeStatusHistoryManager.add_history(
                    recipe_id=recipe_id,
                    recipe_code=recipe["recipe_code"],
                    old_status=old_status,
                    new_status=new_status,
                    changed_by=username,
                    remarks=remarks,
                    correlation_id=correlation_id,
                    _connection=conn,
                )
                user = cursor.execute(
                    "SELECT role FROM users WHERE LOWER(username)=LOWER(?) LIMIT 1",
                    (username,),
                ).fetchone()
                role = user["role"] if user else "UNKNOWN"
                AuditManager.log_event(
                    username=username,
                    role=role,
                    action="RECIPE_STATUS_CHANGED",
                    change_source="RECIPE_APPROVAL_WORKFLOW",
                    recipe_code=recipe["recipe_code"],
                    recipe_version=recipe["version"],
                    record_id=recipe_id,
                    old_value=old_status,
                    new_value=new_status,
                    reason=remarks or f"{old_status} to {new_status}",
                    correlation_id=correlation_id,
                    _connection=conn,
                )

                # Existing approved behavior automatically promotes the approved
                # version to RELEASED, but both transitions now share one commit.
                if new_status == "APPROVED":
                    cursor.execute(
                        "UPDATE recipes SET status='RELEASED', updated_at=CURRENT_TIMESTAMP WHERE id=?",
                        (int(recipe_id),),
                    )
                    RecipeStatusHistoryManager.add_history(
                        recipe_id=recipe_id,
                        recipe_code=recipe["recipe_code"],
                        old_status="APPROVED",
                        new_status="RELEASED",
                        changed_by="SYSTEM",
                        remarks="Auto Release After Approval",
                        correlation_id=correlation_id,
                        _connection=conn,
                    )
                    AuditManager.log_event(
                        username="SYSTEM",
                        role="SYSTEM",
                        action="RECIPE_RELEASED_AFTER_APPROVAL",
                        change_source="RECIPE_APPROVAL_WORKFLOW",
                        recipe_code=recipe["recipe_code"],
                        recipe_version=recipe["version"],
                        record_id=recipe_id,
                        old_value="APPROVED",
                        new_value="RELEASED",
                        reason="Auto Release After Approval",
                        correlation_id=correlation_id,
                        _connection=conn,
                    )
            return True, "Status Updated"
        except Exception as exc:
            return False, f"Status update failed and was rolled back ({type(exc).__name__})."
