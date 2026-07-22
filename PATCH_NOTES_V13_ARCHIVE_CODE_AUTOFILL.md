# CRS V13 Archive Recipe Code Autofill Patch

## Purpose

Improves the Archive Recipe confirmation page so the selected recipe code is filled automatically and shown as read-only. The user only enters the archive reason and presses **Archive Recipe**.

## Behavior

- Archive action: recipe code is populated automatically from the selected database recipe.
- The code field is read-only and is still submitted to the existing server-side exact-code validation.
- Restore and permanent-delete actions retain their existing manual confirmation safeguards.
- Permanent deletion still requires both the exact recipe code and `DELETE`.

## Files

- `flask_app/templates/recipes/recipe_retention_confirm.html`
- `tests/safe/test_recipe_archive_code_autofill.py`

## Migration

No database migration or bootstrap is required.
