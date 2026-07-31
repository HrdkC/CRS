# Test evidence

## Completed in this implementation session

- Git whitespace/error scan: passed.
- Static Python delimiter/string sanity scan for all changed Python files: passed.
- Jinja block-balance scan for changed templates: passed.
- CSS production bundle rebuilt from 37 ordered modules: passed.
- Workflow migration rehearsed on a current database copy: 8 workflows and 56 steps backfilled.
- Migration-copy SQLite integrity: `ok`.
- Migration-copy foreign-key violations: `0`.
- Rollback-copy domain row counts preserved: machines 4, recipes 12, parameters 619.
- Rollback-copy SQLite integrity: `ok`.
- Rollback-copy foreign-key violations: `0`.
- Current P15 Second Stage recipe groups: `CAP_STRIP_SIDE`, `BT_SIDE` only.
- Real PLC connections, reads, and writes: not performed.

## Pending target runtime

- Python `compileall` and pytest require the workstation virtual environment under the scheduled deployment account; the Codex sandbox cannot execute its protected base Python.
- Authenticated browser viewport and screenshot evidence requires the SYSTEM-owned scheduled CRS stack to be running.
- Supervised PLC tests remain `PENDING SUPERVISED LIVE PLC TEST`.

Required commands after the scheduled stack is restarted:

```powershell
.\venv\Scripts\python.exe -m compileall -q app.py database flask_app scripts
.\venv\Scripts\python.exe -m pytest -q tests\safe\test_configuration_workflow_v13.py tests\safe\test_configuration_workflow_security.py tests\safe\test_parameter_template_guided_setup.py tests\safe\test_plc_tag_browser_configuration_return.py
.\venv\Scripts\python.exe -m pytest -m safe
```

