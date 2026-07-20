# CRS V11.11-RC1 agreement compliance matrix

| Agreement | V11.11-RC1 status | Evidence / remaining gate |
|---|---|---|
| Flask/Python browser intranet | Implemented | Flask remains the web application; Waitress runner added |
| SQLite development database | Implemented and hardened | Central connection policy, FK enforcement, timeout and controlled migration added |
| MySQL preferred production database | Pending external program | Connectivity/profile support remains; SQLAlchemy/Alembic equivalence is not complete |
| Allen-Bradley via pycomm3 | Implemented with safety gates | Web process queues work; dedicated worker requires explicit communication gates |
| Current RELEASED values editable with audit | Implemented in canonical path | Value and correlated audit now commit atomically; unchanged values create no audit |
| Historical released versions read-only | Implemented in canonical path | Legacy writes are blocked by default; regression coverage retained |
| Final roles incl. VIEWER | Implemented | Session guard revalidates active user and DB role on protected requests |
| Existing active session has priority | Implemented atomically | Case-insensitive unique active-session claim plus persisted blocked-login audit |
| Immediate authority revocation | Implemented | Disable, role change and admin password reset revoke sessions/locks |
| DB-backed resource locks | Implemented atomically | Unique current claims, session/token ownership, lease/fencing metadata |
| Long PLC jobs durable | Implemented foundation | Dedicated worker, queued claims, heartbeat and stale recovery; site service test pending |
| P15 FS recipe arrays REAL[500] | Implemented | Stage-specific helper definitions and tests |
| P15 SS recipe arrays REAL[150] | Implemented | Stage-specific helper definitions and tests |
| P15 SS CAP_STRIP + BT only | Implemented | SHAPING and legacy SS stop/position purposes are filtered/deactivated |
| P15 SS selection-only phase data | Implemented in active paths | UI, service, import/export, readiness and PLC payload use selection-only contract |
| No partial recipe download | Preserved | Full validation and operation manager remain; supervised PLC negative tests pending |
| GUI-configurable PLC mapping | Preserved | Existing stage readiness/registry retained |
| Clean patch/full replacement delivery | Implemented | Allowlist builder rejects DB, secret, backup, Git, venv, log and generated work files |
| Safe automated tests | Implemented | Default pytest discovers only `tests/safe`; PLC driver/network are blocked |
| Production HTTPS/Windows service | Assets added, site test pending | Waitress and worker launchers added; TLS/firewall/service rehearsal requires target Windows system |
| Backup/restore/rollback | Procedure documented, drill pending | Must be executed on target environment before production approval |
| Authenticated visual/accessibility QA | Pending external browser run | Static route/template/CSS checks pass; target-browser evidence required |
| Supervised FS/SS PLC commissioning | Pending | No live PLC connection was made during hardening |
| AI/ML advisory only | Preserved | No AI has recipe approval/write/PLC authority |
