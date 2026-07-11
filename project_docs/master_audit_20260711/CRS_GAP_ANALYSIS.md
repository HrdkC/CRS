# CRS Gap Analysis

## P0 - Must Close Before Plant Production

| Gap | Risk | Required evidence |
|---|---|---|
| Live PLC end-to-end acceptance not run | Incorrect transfer or handshake behavior | Controlled FS and SS restore/save/upload/download/readback test record |
| Full browser visual validation unavailable in this run | Responsive overlap or inaccessible action may remain | Approved desktop/tablet/mobile screenshots for all critical routes |
| MySQL runtime migration incomplete | Production backend cannot be switched safely | All active managers migrated, Alembic upgrade/rollback drill, parity tests |
| Backup restore drill not completed | Recovery plan may fail under outage | Timed restore to spare workstation with integrity and login verification |
| Production HTTPS/service not commissioned | Cookie and transport protections incomplete | Trusted host, TLS, service restart, log rotation and health probe evidence |
| Legacy script tests can touch DB/PLC | Accidental unsafe test execution | Quarantine or convert to isolated pytest with temp DB and mocked pycomm3 |

## P1 - Production Hardening

| Gap | Current mitigation | Next action |
|---|---|---|
| CSP permits inline script/style | Other browser headers enabled | Remove inline handlers/styles and adopt nonces or external assets |
| Login throttle is process-local | Attempt logging and throttling exist | Store counters centrally for multi-process deployment |
| App startup performs schema/default checks | Failures warn and generic bootstrap exists | Move all schema/data changes to explicit migrations |
| Runtime DB layer mixes sqlite3 and SQLAlchemy | Parameterized SQL is common | Complete repository/service abstraction |
| Dependency lock is not hash-pinned | `pip-audit` found no known CVEs | Add lock generation, SBOM and scheduled audit |
| Route authorization needs full matrix tests | Role guards and global session guard exist | Test every state-changing route for every role |
| Log retention/monitoring is not commissioned | Audit tables and reports exist | Define rotation, alerting, capacity and archive restore tests |

## P2 - Maintainability and Product Quality

- Further reduce large CSS override modules and verify every breakpoint visually.
- Replace remaining broad exception handlers with typed failure categories.
- Add pagination/query caps where older list routes still load whole datasets.
- Add actionable dashboards only from trusted production data, not decorative charts.
- Add localization and terminology governance if deployment expands beyond one plant.

## Pass-One Fixes Completed

- Bootstrap `--help` is now non-mutating.
- Generic recovery no longer exposes machine-specific P15 data migration.
- Optional bootstrap failure cannot be reported as success.
- Production secret, secure cookie and trusted host requirements fail closed.
- CSRF, session guard and browser-header setup fail closed.
- Unsafe DOM insertion in shared login/operation messages was removed.
- PLC registry IP addresses are validated before storage or ping use.
- Health, repository audit and release validation tools were added.
