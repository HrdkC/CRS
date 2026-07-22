# CRS V11.11-RC1 Startup Import Compatibility Fix

## Cause

The Restore Buffer Persistence patch added `PLC_RESTORE_VERIFY_DELAY_SECONDS`
to `config/settings.py` and imported it from the PLC buffer operation manager.
The later Full Automatic Deployment patch also replaced `config/settings.py`,
but its copy did not include that restore setting. Applying the later patch over
the former therefore caused an application-startup `ImportError`.

## Fix

- Keeps the delayed restore persistence setting.
- Keeps all automatic PLC worker supervision settings.
- Adds safe parsing for an invalid delay environment value.
- Adds a compatibility fallback in the PLC buffer manager so a partially
  applied settings patch cannot prevent the whole CRS application from starting.

## No migration

No database migration or bootstrap is required.
