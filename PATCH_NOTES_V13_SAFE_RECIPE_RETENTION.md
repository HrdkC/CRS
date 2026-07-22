# CRS V13 Safe Recipe Retention Patch

Baseline: `Centralized_Recipe_System_Codex_V13_22072026.zip`

## Purpose

Adds a controlled way to remove unused recipes from the active recipe list without destroying production traceability.

## Workflow

1. **Archive** — ADMIN only; allowed for DRAFT, REVIEW, or APPROVED recipes that are not locked and have no active PLC job.
2. **Restore** — ADMIN only; returns an archived recipe to the active list with its previous lifecycle status unchanged.
3. **Permanent Delete** — ADMIN only and only after Archive. Restricted to TEST ONLY DRAFT recipes that:
   - never entered REVIEW, APPROVED, or RELEASED;
   - have no released sibling under the same recipe code;
   - have no PLC operation, upload, or download history;
   - have no retained version snapshot;
   - have no active job or resource lock.

Released/current-production recipes are protected and cannot be archived or deleted.

## Audit and retention

Archive, restore, and permanent delete are atomic with the general audit record. Permanent delete retains:

- `audit_log` evidence;
- parameter/phase audit evidence;
- a durable `recipe_retention_history` tombstone with deleted row counts and correlation ID.

## Schema migration

The migration adds archive metadata columns to `recipes`, creates `recipe_retention_history`, and records schema version `CRS_V13_RECIPE_RETENTION_001`.

Run while CRS is stopped:

```powershell
.\venv\Scripts\python.exe .\scripts\upgrade_recipe_retention_v13.py
```

Expected result:

```text
Recipe retention migration: SUCCESS
SQLite integrity         : ok
Foreign-key violations   : 0
```

## UI

Active recipe list:

- `Archived Recipes` button for ADMIN;
- `Archive` action only when allowed;
- `Protected` status for released/current/locked recipes.

Archived recipe list:

- Restore;
- History;
- restricted Permanent Delete with explicit confirmation.

## Validation performed

- targeted safe retention tests: 3 passed;
- migration against a disposable copy of the supplied V13 database: passed;
- SQLite integrity: ok;
- foreign-key violations: 0;
- archive/delete trial on disposable GT_TEST recipe: passed;
- Python syntax compilation: passed;
- Jinja template parsing: passed.

The complete safe suite was not executable in the build container because Flask and pycomm3 are not installed there. No real PLC connection or write was performed.
