# CRS V13.1 Configuration UX Redesign

This patch replaces the standard configuration entry path with a persistent, validated seven-step journey. Existing PLC communication, recipe operations, automatic deployment, watchdog, retention, restore, and download behavior is preserved.

Apply only after backing up `database/recipe.db`. Run `scripts/upgrade_configuration_workflow_v13.py`, restart the scheduled CRS stack, and perform an authenticated browser acceptance. Roll back with `scripts/rollback_configuration_workflow_v13.py`; rollback does not alter domain configuration.

No database, secret, SMTP/email/OTP feature, PLC runtime file, log, backup, virtual environment, cache, or Git metadata belongs in this patch.

