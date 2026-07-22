# CRS V11.11-RC1 — Recipe Parameter Edit Transaction Fix

## Confirmed cause

`RecipeParameterValueManager.update_recipe_value()` uses the centralized
`transaction(immediate=True)` context manager, but
`database/recipe_parameter_value_manager.py` imported only `get_connection`.
The resulting `NameError` was caught by the fail-safe exception handler, which
showed "Recipe parameter update failed and was rolled back."

## Correction

- Import `transaction` from `database.database`.
- Keep the recipe value update, parameter audit, and general audit in one atomic
  transaction.
- Log unexpected failures with the correlation ID.
- Show a short non-sensitive reference ID in the operator error message.
- Add a regression test proving a valid edit commits the value and both audits.

## Database impact

No schema migration or bootstrap is required.

## Apply

Stop CRS, extract this patch over the project root, restart the application, and
perform a hard browser refresh.

## Test

```powershell
python -m pytest -q tests/safe/test_recipe_parameter_value_edit_success.py
```

Expected: `1 passed`.
