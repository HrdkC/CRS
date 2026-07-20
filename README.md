# Centralized Recipe System — V11.11-RC1

Industrial recipe-management application for PCR Tyre Building Machines using Flask, SQLite for development, a staged SQLAlchemy/MySQL migration path, and `pycomm3` for Allen-Bradley ControlLogix communication.

## Safety status

This release is a hardened engineering release candidate. Automated tests never communicate with a PLC. Live PLC commissioning remains a separately supervised activity. Do not enable the PLC worker until the machine/stage mapping, interlocks, tag contract and commissioning worksheet are approved.

Key rules:

- Current RELEASED recipe values are editable only by authorized roles, with atomic audit.
- Historical RELEASED versions are read-only.
- P15 Second Stage recipe phase data contains only CAP_STRIP_SIDE and BT_SIDE selections.
- SHAPING_SIDE, Second Stage stop, and Second Stage position are not recipe data.
- First Stage recipe arrays are REAL[500]; Second Stage arrays are REAL[150].
- Legacy recipe-table mutations are blocked by default.
- The web process queues PLC jobs; the separately supervised worker executes them.

## Clean replacement procedure

1. Stop the CRS web service and PLC worker.
2. Back up the existing project and verify a copy of `database/recipe.db` can be opened.
3. Extract this clean replacement into a new folder. Do not overwrite the only working installation.
4. Copy only the existing operational database into `database/recipe.db`. Do not copy the old `venv`, `instance/crs_secret_key`, logs, caches or backup folders.
5. Create a fresh virtual environment and install dependencies:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

6. Generate a new machine-local session secret:

```powershell
python scripts/configure_secret_key.py
```

7. Back up the database again, then run the controlled bootstrap/migrations:

```powershell
python scripts/bootstrap_crs_system.py --no-seed-users --strict
python -m database.hardening_schema_manager
```

8. Run safe validation:

```powershell
python -m compileall app.py config database flask_app helper plc recipe scripts tools utils tests wsgi.py
python -m pytest
python scripts/build_css_bundle.py --check
python scripts/run_crs.py --check
```

9. Start the web application through Waitress:

```powershell
run_crs.bat
```

## Initial administrator

No predictable default password is created. Create the first administrator interactively:

```powershell
python scripts/create_admin.py
```

Keep the generated/entered credential outside source control and require a password change under the approved site policy.

## PLC worker

The PLC worker is disabled by default and requires both gates:

```powershell
$env:CRS_PLC_WORKER_ENABLED = "1"
$env:CRS_ALLOW_PLC_COMMUNICATION = "YES"
python scripts/run_plc_worker.py
```

Run it only as a separately supervised service after commissioning approval. Do not set these variables in developer terminals, CI, or general web-service environments.

## Safe and live tests

Default `pytest` collection is limited to `tests/safe`. The test harness blocks external network connections and replaces `pycomm3.LogixDriver` with a fail-closed stub.

Live PLC utilities are under `tools/plc_live_manual` or explicitly guarded support scripts. They require an interactive terminal, `CRS_ALLOW_LIVE_PLC_TESTS=YES`, and exact typed confirmation.

## Production configuration

For production, configure at minimum:

```powershell
$env:CRS_DEPLOYMENT_MODE = "production"
$env:CRS_COOKIE_SECURE = "1"
$env:CRS_TRUSTED_HOSTS = "crs-host.example.local"
$env:CRS_ALLOW_STARTUP_MIGRATIONS = "0"
```

Use an approved HTTPS reverse proxy or TLS termination, a least-privilege Windows service account, restricted firewall rules, rotated secrets, log rotation, monitored health endpoints, and verified backup/restore procedures.

Health endpoints:

- `/health/live`
- `/health/ready`

## Database policy

- SQLite remains the active development/runtime database for this RC.
- Foreign keys and busy timeout are enabled centrally.
- WAL and synchronous policy are configurable.
- MySQL connection testing does not mean runtime equivalence is complete.
- Do not activate MySQL production runtime until repository conversion, Alembic migration, reconciliation and rollback tests pass.

## Release contents

The clean release intentionally excludes:

- `.git` history;
- virtual environments;
- databases and SQLite sidecars;
- `instance` secrets/profiles;
- backups;
- logs and caches;
- recipe import/export working files;
- local PLC/environment detail files;
- debug-search artifacts.

See `project_docs/current/` for the current agreement register, release status, migration status, commissioning status and remaining limitations.
