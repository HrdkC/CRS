# CRS V13 Permanent Delete Single-Action Patch

## Purpose

Remove the additional `Type DELETE` field from the permanent-delete confirmation page.
The user has already selected **Delete Permanently** from the archived recipe list and
then presses the final red **Delete Permanently** button on the confirmation page.

## Safety controls retained

- ADMIN-only route/capability check.
- CSRF-protected POST request.
- Recipe ID comes from the selected archived recipe URL.
- Recipe code is populated from the database and remains read-only.
- Mandatory deletion reason (minimum five characters).
- Recipe must be archived.
- Recipe must be an eligible TEST ONLY DRAFT.
- No lifecycle, released-version, PLC operation, upload/download, version-snapshot,
  active-job, or active-lock history may exist.
- Atomic transaction, audit event, and durable deletion tombstone remain unchanged.

## Files changed

- `flask_app/templates/recipes/recipe_retention_confirm.html`
- `flask_app/routes/recipe_routes.py`
- `database/recipe_retention_manager.py`
- `tests/safe/test_recipe_permanent_delete_single_action.py`

## Database migration

None.
