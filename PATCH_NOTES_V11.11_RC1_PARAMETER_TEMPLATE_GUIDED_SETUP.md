# CRS V11.11-RC1 — Guided Parameter Template Setup Patch

Apply over the approved V11.11-RC1 baseline after the responsive-header patch.

This patch adds:

- configured numeric PLC-array dropdown on Parameter Template;
- automatic configured range selection and row-count preview;
- safe creation of missing parameter rows only;
- no PLC read or PLC write during template creation;
- transactional recipe-value backfill for existing recipes;
- one-table bulk editing of names, units, limits, defaults, and Used status;
- JSON submission of changed rows only, avoiding large form-part limits;
- transaction-scoped audit with correlation IDs;
- clearer Configuration Readiness action label.

No SMTP, email, OTP, or V11.12 functionality is included.
