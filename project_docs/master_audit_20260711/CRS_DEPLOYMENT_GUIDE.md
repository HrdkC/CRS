# CRS Deployment Guide

## Workstation Setup

1. Restore the project folder from the approved release package.
2. Open Command Prompt or PowerShell in the project root.
3. Run `setup_crs.bat`.
4. Review `reports/bootstrap/` and require `SUCCESS`.
5. Run `run_crs.bat` for development validation.

The setup runner creates/reuses a virtual environment, installs pinned requirements, creates a private machine-local session-signing key, builds the CSS bundle, runs generic schema bootstrap, and imports the app. It never prints the signing key and never runs machine-specific recipe/phase migrations.

The default key file is `instance/crs_secret_key`. It is excluded from source control and must be included in the workstation's protected configuration backup. To use an approved secret store instead, set `CRS_SECRET_KEY`; to use another protected file, set `CRS_SECRET_KEY_FILE`.

## Production Environment

Set environment variables through the approved Windows service or secret-management mechanism:

```powershell
$env:CRS_DEPLOYMENT_MODE = "production"
# Option A: approved service environment secret
$env:CRS_SECRET_KEY = "<approved random secret>"
# Option B: protected machine file created by setup_crs.bat
# $env:CRS_SECRET_KEY_FILE = "D:\CRS-Secrets\crs_secret_key"
$env:CRS_COOKIE_SECURE = "1"
$env:CRS_TRUSTED_HOSTS = "crs-hostname,crs-host-ip"
$env:CRS_HOST = "127.0.0.1"
$env:CRS_PORT = "5000"
$env:CRS_THREADS = "6"
$env:CRS_ALLOW_STARTUP_MIGRATIONS = "0"
venv\Scripts\python.exe scripts\run_crs.py
```

Place Waitress behind an approved HTTPS reverse proxy. Configure proxy trust only for the exact deployment topology. Do not expose Flask debug mode or the development server.

Production startup does not mutate schema or phase defaults unless `CRS_ALLOW_STARTUP_MIGRATIONS=1` is explicitly set. Keep it disabled and run reviewed migrations before service start.

Never run `scripts\configure_secret_key.py --force` during normal operation. Forced rotation invalidates all signed browser sessions and requires a controlled service restart.

## Service Monitoring

- Liveness: `GET /health/live`
- Readiness: `GET /health/ready`
- Restart only after repeated failed readiness and operator/job-state review.
- Do not infer PLC download success from process health. Use PLC operation history and readback verification.

## Pre-Release Checks

```powershell
venv\Scripts\python.exe -m pytest tests\safe -q
venv\Scripts\python.exe scripts\validate_crs_release.py
venv\Scripts\python.exe scripts\run_crs.py --check
```

Production approval additionally requires the P0 evidence in `CRS_GAP_ANALYSIS.md`.

References: [Flask production deployment](https://flask.palletsprojects.com/en/stable/deploying/), [Flask Waitress guidance](https://flask.palletsprojects.com/en/stable/deploying/waitress/), and [Flask proxy guidance](https://flask.palletsprojects.com/en/stable/deploying/proxy_fix/).
