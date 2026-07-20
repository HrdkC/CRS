# Migration status

Applied hardening migration identifier: `CRS_V11_11_HARDENING_001`.

Adds/updates:

- current resource claim table and lease/fencing metadata;
- one-active-session unique index;
- database-backed login throttling;
- audit correlation IDs;
- phase-control row version and phase audit table;
- PLC job worker/recovery fields;
- case-insensitive username uniqueness.

Run only after a verified database backup:

```powershell
python scripts/bootstrap_crs_system.py --no-seed-users --strict
python -m database.hardening_schema_manager
```

MySQL runtime migration is not complete and remains blocked pending SQLAlchemy repository and Alembic equivalence work.
