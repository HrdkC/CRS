# CRS Backup and Restore Guide

## Backup

1. Confirm no recipe save/import or PLC operation is active.
2. Stop the CRS Windows service.
3. Copy `database/recipe.db` to the protected backup location with timestamp and release version.
4. Copy application configuration excluding plaintext secrets.
5. Hash the database backup and record size, UTC time and operator.
6. Restart CRS and verify readiness.

SQLite online backup APIs should replace file copy when continuous service is required. Never copy a live file without a verified method.

## Restore to Replacement Workstation

1. Install the exact approved CRS release and Python architecture.
2. Run `setup_crs.bat` without default user seeding unless recovery authorization exists.
3. Stop CRS.
4. Preserve the newly created empty database separately.
5. Restore the approved database as `database/recipe.db`.
6. Run integrity and release validation.
7. Start CRS and verify login, roles, configuration, current recipes and audit history.
8. Keep PLC writes disabled until machine/stage mappings and program revisions are reviewed.

## Verification

```powershell
venv\Scripts\python.exe -c "import sqlite3; c=sqlite3.connect('database/recipe.db'); print(c.execute('PRAGMA integrity_check').fetchone()[0]); c.close()"
venv\Scripts\python.exe scripts\validate_crs_release.py
```

## Recovery Acceptance

Record elapsed time, backup identity, application version, database hash, validation result, user and approval. Perform a scheduled restore drill; an untested backup is not a recovery plan.
