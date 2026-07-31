# Known limitations — V13.1

- Live PLC commissioning was not performed by the automated hardening process.
- The numeric DOWNLOAD_RESULT meaning requires controls-engineering approval.
- SQLite remains in use; full SQLAlchemy/Alembic/MySQL parity is not complete.
- Existing legacy tables are retained for reconciliation, but mutations are blocked by default.
- Some older managers still contain compatibility schema helpers; production must run controlled bootstrap/migration before startup and disable startup migrations.
- Final authenticated operator acceptance remains required on the target plant browser/workstation.
- The durable PLC worker is automatically supervised by the deployed CRS stack; a Windows service migration remains a future production-hardening option.
