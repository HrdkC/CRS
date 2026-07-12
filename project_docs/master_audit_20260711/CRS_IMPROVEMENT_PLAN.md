# CRS Improvement Plan

## Gate 1 - Controlled PLC Acceptance

1. Freeze a database backup and PLC program revision.
2. Verify exact machine/stage identity before every operation.
3. Test restore, recipe save, PLC upload, and PLC download separately.
4. Prove manual mode, download enable, request, complete, error and readback behavior.
5. Prove First Stage and Second Stage phase arrays independently.
6. Retain screenshots, audit rows, PLC values, user, reason and timestamps.

Exit: zero partial transfers, correct readback, clear failure messages, no production logic impact.

## Gate 2 - Safe Automated Regression

- Convert critical workflow tests to pytest fixtures using a temporary SQLite database.
- Mock all pycomm3 calls by default.
- Mark any live PLC test explicitly and require an environment opt-in.
- Add role matrix, historical lock, released edit audit, import/export and concurrency tests.

Exit: one safe command can run locally and in CI without touching plant PLCs or the production DB.

## Gate 3 - Database Portability

- Move active sqlite3 managers behind SQLAlchemy repositories.
- Introduce Alembic revisions with upgrade and downgrade procedures.
- Eliminate SQLite-only SQL and schema mutation at app startup.
- Validate SQLite and MySQL from the same behavioral suite.

Exit: MySQL switch requires configuration and migration only, not feature code changes.

## Gate 4 - Production Operations

- Run Waitress behind approved HTTPS termination.
- Set trusted hosts, secure cookies, secret rotation and least-privilege service account.
- Install monitored Windows service with restart policy.
- Configure log rotation, backup schedule, health probes and capacity alerts.
- Perform disaster-recovery drill.

## Gate 5 - UI and Analytics

- Treat `main.css` as the ordered source manifest and run `scripts/build_css_bundle.py` after CSS module changes.
- Extend progressive HTML updates only after the Audit History pilot passes real-browser acceptance.
- Complete browser evidence at 1920x1080, 1366x768, tablet and mobile widths.
- Prioritize task status, exceptions and trend analysis over decorative visualization.
- Add analytics only after outcome/quality labels are governed and traceable.
