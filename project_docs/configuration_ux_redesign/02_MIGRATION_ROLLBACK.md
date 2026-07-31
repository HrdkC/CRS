# Migration and rollback

## Apply

Back up `database/recipe.db`, stop CRS, then run:

```powershell
.\venv\Scripts\python.exe .\scripts\upgrade_configuration_workflow_v13.py
```

The migration creates and backfills only:

- `configuration_workflows`
- `configuration_workflow_steps`
- schema version `CRS_V13_CONFIGURATION_WORKFLOW_001`

It does not change machine, PLC, tag, parameter, phase, recipe, user, audit, or operation records.

## Rollback

Stop CRS, retain the database backup, then run:

```powershell
.\venv\Scripts\python.exe .\scripts\rollback_configuration_workflow_v13.py
```

Rollback removes only the workflow tracking tables and schema-version row. The existing Configuration Readiness engineering page remains available.

