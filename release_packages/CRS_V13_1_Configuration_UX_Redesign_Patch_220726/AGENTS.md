# CRS repository instructions

## Read first

1. Read `project_docs/current/00_READ_FIRST_CURRENT.md` and `project_docs/current/CURRENT_RELEASE.md` before editing.
2. Treat `plc_registry` as the PLC source of truth. `plc_master` is legacy import data only.
3. Keep templates, mappings, recipes, and phase controls owned by Machine + Stage.

## Safety contracts

- Never contact a real PLC from automated tests. `pytest -m safe` must use mocks and temporary databases.
- Never permit a partial recipe download.
- Preserve historical recipe and audit evidence.
- Store timestamps in UTC and convert to IST in the UI.
- P15 Second Stage recipe phase data contains `CAP_STRIP_SIDE` and `BT_SIDE` selections only. `SHAPING_SIDE`, stop, and position are PLC-fixed, non-recipe data.
- AI and analytics are advisory only. They cannot approve, release, alter, or download a recipe.

## Configuration UX

- `/configuration` is the machine/stage setup center.
- `/configuration/<machine>/<stage>/setup` is the standard seven-step journey.
- Keep raw PLC rules and repair controls in Engineering Tools, not the standard journey.
- Progress is validated from live readiness data and tracked in `configuration_workflows` and `configuration_workflow_steps`.
- Parameter-template creation must show a read-only preview before committing rows.
- Every mutation requires backend authorization, CSRF protection, a reason where applicable, an atomic transaction, and audit evidence.

## Delivery

- Use `venv\Scripts\python.exe -m ...` from the repository root on Windows.
- Build `flask_app/static/css/crs.bundle.css` after changing CSS modules.
- Exclude databases, secrets, `.git`, virtual environments, logs, caches, backups, PLC runtime files, and imports/exports from release ZIPs.
- Report tests actually run and clearly mark PLC/browser/deployment checks that were not run.

