# CRS Database Configuration

## Current Support

| Backend | Status |
|---|---|
| SQLite | Complete development/runtime backend |
| MySQL | Connection components exist; active application migration incomplete |
| MSSQL | Architectural future target only |

`CRS_DATABASE_URL` does not make the full runtime database independent today. Many active managers still use `sqlite3` and `DATABASE_PATH`. The bootstrap intentionally stops after testing a non-SQLite connection rather than creating a partial schema.

## SQLite Configuration

Default database: `database/recipe.db`.

```powershell
$env:CRS_DATABASE_URL = "sqlite:///C:/CRS/data/recipe.db"
```

The current legacy managers still expect the project `DATABASE_PATH`; use the default until the repository migration is complete.

## Future MySQL Configuration

```powershell
$env:CRS_DATABASE_URL = "mysql+pymysql://crs_app:<secret>@db-host:3306/crs"
```

Before enabling:

1. Create a dedicated database and least-privilege application account.
2. Migrate all active managers to SQLAlchemy repositories.
3. Create Alembic revisions for every table/index/default.
4. Run upgrade, rollback and data parity tests on a disposable database.
5. Back up SQLite and verify record counts/checksums after migration.

## Configuration Page Gap

A safe GUI database-switch page is not implemented. A production GUI must never display saved passwords, must test connectivity before save, must require superuser re-authentication and reason, and must not switch the active database while requests or PLC jobs are running.

References: [SQLAlchemy connection pooling](https://docs.sqlalchemy.org/en/20/core/pooling.html), [Alembic migrations](https://alembic.sqlalchemy.org/en/latest/), and [MySQL account least privilege](https://dev.mysql.com/doc/refman/8.4/en/creating-accounts.html).
