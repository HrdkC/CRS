# Known limitations — V11.11-RC1

- Live PLC commissioning was not performed by the automated hardening process.
- The numeric DOWNLOAD_RESULT meaning requires controls-engineering approval.
- SQLite remains in use; full SQLAlchemy/Alembic/MySQL parity is not complete.
- Existing legacy tables are retained for reconciliation, but mutations are blocked by default.
- Some older managers still contain compatibility schema helpers; production must run controlled bootstrap/migration before startup and disable startup migrations.
- Authenticated visual regression and accessibility checks require the target browser/Windows environment.
- The durable PLC worker must be installed and supervised as a separate service at the site.
