# CRS V11.11-RC1 implementation and validation report

## Baseline

- Source archive: `Centralized_Recipe_System_Codex_V11.1_RC_17072026(1).zip`
- Embedded baseline commit: `5b954ffaa16497e31e4805f29672500a167598de`
- Hardening branch: `hardening/v11-11-agreement-compliance`
- New release identity: `V11.11-RC1`

## Implemented hardening

### Clean release and credential containment

- Added an allowlist-based replacement-ZIP builder.
- Excluded Git history, virtual environments, databases, secrets, backups, logs, caches, imports/exports and generated workstation files.
- Removed predictable default password behavior and added secure administrator/bootstrap flows.
- Added secret/forbidden-path validation and per-file SHA-256 manifest generation.

### Safe test boundary

- Default pytest discovery is limited to `tests/safe`.
- External network connections and real `pycomm3.LogixDriver` construction are blocked during safe tests.
- Direct PLC scripts were moved to `tools/plc_live_manual` and require explicit environment plus interactive gates.
- CI definition uses a fresh environment, temporary database and PLC mocks.

### Database and transaction integrity

- Centralized SQLite connection configuration with foreign-key enforcement and busy timeout.
- Added a controlled V11.11 schema migration and read-only production schema preflight.
- Removed schema creation from high-traffic request managers.
- Made canonical single-value, bulk, Excel-update, phase, approval, release, create, copy and snapshot-restore workflows transactional with correlated audit.
- Audit failures roll back business data.
- Legacy recipe mutations are blocked by default.

### Concurrency, sessions and authority

- Added atomic unique resource claims with session/token ownership, lease and fencing metadata.
- Added atomic one-active-session-per-normalized-username enforcement.
- Moved login throttling to the database.
- Disabled/demoted/password-reset users have active sessions and resource locks revoked.
- Protected requests revalidate the current database role and active state.

### Durable PLC operations

- Flask requests now queue PLC jobs instead of starting daemon PLC threads.
- Added a separate fail-closed PLC worker with atomic job claiming, heartbeat, stale-job recovery and deterministic terminal states.
- Job status access now applies capability/ownership checks.
- No real PLC communication occurs unless both worker and communication gates are explicitly enabled.

### P15 contract closure

- First Stage data array size is resolved as 500.
- Second Stage data array size is resolved as 150.
- Second Stage recipe phase groups are CAP_STRIP_SIDE and BT_SIDE only.
- SHAPING_SIDE, Second Stage stop and Second Stage position are excluded from active recipe phase payload, readiness and UI paths.
- Existing incompatible Second Stage data/rules are deactivated or cleared by migration without dropping history columns.
- DOWNLOAD_RESULT remains DINT; numeric semantics still require controls approval.

### Production foundations

- Added WSGI/Waitress runner.
- Added separate PLC-worker launchers.
- Added health/schema fail-closed behavior.
- Added current documentation, deployment limitations and definitive continuation prompt.

## Validation executed

All validation used a temporary/disposable database and blocked PLC networking.

- Python compileall: PASS.
- Safe pytest: **40 passed**.
- Controlled migration on disposable copy of supplied DB: PASS.
- SQLite integrity check: `ok`.
- Foreign-key check: `0` violations.
- Active duplicate usernames after migration: `0`.
- Active P15 SS non-CAP/BT phase rows: `0`.
- P15 SS stop/position values after migration: `0`.
- Safe startup check: PASS.
- CSS production bundle check: PASS.
- Jinja templates compiled: `62`.
- Route/method combinations checked: `152`.
- Safe GET status: `55 × 200`, `14 × 302`, `1 expected × 404`.
- Rendered links checked: `2,656`.
- Rendered forms checked: `403`.
- Unique internal targets checked: `970`.
- Broken safe target/form action: `0`.
- Clean release policy: PASS.
- Git whitespace/error check: PASS.

## Not executed and not claimed

- No live PLC connection/read/write.
- No supervised P15 FS or SS commissioning.
- No controls approval of DINT result-code meanings.
- No target Windows service installation/restart test.
- No HTTPS/reverse-proxy/firewall commissioning.
- No authenticated target-browser screenshot/accessibility run.
- No production backup restoration or rollback drill.
- No complete SQLAlchemy/Alembic/MySQL equivalence test.

## Release classification

`V11.11-RC1` is a clean, hardened engineering replacement baseline. It is not a plant-production approval. Production classification requires all manual/external gates in `COMMISSIONING_STATUS.md` and `KNOWN_LIMITATIONS.md` to be closed and signed.
