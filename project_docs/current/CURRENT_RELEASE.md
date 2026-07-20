# CRS V11.11-RC1 current release

Baseline: V11.1 RC workspace / embedded commit `5b954ffaa16497e31e4805f29672500a167598de`.

Implemented in this hardening release:

- atomic database-backed recipe/PLC resource claims;
- atomic single-active-user session constraint;
- database-backed login throttling;
- immediate session revocation on user disable, role change and administrative password reset;
- atomic single-value and bulk recipe edits with correlated audit;
- atomic phase-sequence save with reason and row audit;
- Second Stage phase-selection-only behavior;
- canonical recipe create/copy transaction hardening;
- legacy recipe mutation block by default;
- durable queued PLC worker with stale-job recovery;
- stage-specific FS=500 and SS=150 support tools;
- safe pytest boundary and guarded live PLC tools;
- Waitress/worker launchers;
- clean release builder and safe CI;
- no predictable default account passwords.

Still requires external/manual completion before plant production:

- supervised FS and SS PLC commissioning;
- approved DINT result-code semantics;
- Windows service/TLS/firewall deployment rehearsal;
- backup restore and rollback drill;
- complete SQLAlchemy/Alembic/MySQL equivalence program;
- authenticated multi-resolution visual/accessibility acceptance;
- final controls, technology, production, IT/security and software sign-off.
