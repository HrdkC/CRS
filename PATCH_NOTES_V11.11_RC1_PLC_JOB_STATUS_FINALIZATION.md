# CRS V11.11-RC1 — PLC Job Status Finalization and Browser Recovery Fix

## Confirmed symptom

A Recipe Restore could write the new value into `CRS_Recipe_Data`, while the browser remained locked at approximately 93% and displayed:

`Status connection interrupted. CRS is retrying; the PLC operation remains locked.`

## Root cause

The PLC write and the browser progress display use separate processes and a shared SQLite job table.

The worker successfully wrote the PLC value, but a transient SQLite busy/locked condition could prevent the final 97%/100% job update from being persisted. The operation manager treated status publishing as best-effort, so the worker could release its resource locks while the database row remained `RUNNING` at the last successful progress value. The browser then continued polling a job that could never become terminal.

Repeated `PRAGMA journal_mode` calls on every short-lived database connection also increased the chance of transient lock contention during one-second progress polling.

## Changes

- Applies SQLite journal mode once per process rather than on every connection.
- Adds busy timeout, foreign keys, and synchronous policy to SQLAlchemy connections.
- Caches the successful hardening-schema preflight per process.
- Retries transient `database is locked` / `database is busy` job reads and writes.
- Re-persists the returned terminal PLC result before resource locks are released.
- Adds a safe orphan-job recovery path when the worker is online and idle but an old job remains active.
- Returns retryable no-cache JSON responses for transient status database contention.
- Uses no-store browser polling with request timeout, cache busting, and faster recovery.
- Updates the JavaScript cache version.

## Safety

- No PLC write semantics were changed.
- No recipe values, PLC tags, interlocks, or phase-control rules were changed.
- No database migration is required.
- Existing stuck jobs are recovered as `INTERRUPTED`, not falsely reported as successful.
- Future successful operations are persisted as `SUCCESS` and 100% before locks are released.

## Validation

- Python compilation: passed.
- JavaScript syntax check: passed.
- Jinja template parse: passed.
- Focused safe tests: 4 passed.
- Real PLC connection/read/write: not performed during automated validation.
