# Changed-file inventory

## Workflow and database

- `database/configuration_workflow_schema.py`
- `database/configuration_workflow_manager.py`
- `database/parameter_template_setup_service.py`
- `database/system_bootstrap_manager.py`
- `flask_app/__init__.py`
- `scripts/upgrade_configuration_workflow_v13.py`
- `scripts/rollback_configuration_workflow_v13.py`

## Routes and UI

- `flask_app/routes/configuration_routes.py`
- `flask_app/routes/parameter_routes.py`
- `flask_app/routes/plc_tag_routes.py`
- `flask_app/templates/configuration/index.html`
- `flask_app/templates/configuration/setup_workflow.html`
- `flask_app/templates/parameters/template_setup_options.html`
- `flask_app/templates/base.html`
- `flask_app/static/css/main.css`
- `flask_app/static/css/crs.bundle.css`
- `flask_app/static/css/modules/37_configuration_workflow.css`

## Tests and guidance

- `tests/safe/test_configuration_workflow_v13.py`
- `tests/safe/test_configuration_workflow_security.py`
- `tests/safe/test_parameter_template_guided_setup.py`
- `tests/safe/test_plc_tag_browser_configuration_return.py`
- `tests/browser/test_configuration_workflow_browser.py`
- `AGENTS.md`
- `project_docs/current/CURRENT_RELEASE.md`
- `project_docs/current/COMPLIANCE_MATRIX.md`
- `project_docs/current/KNOWN_LIMITATIONS.md`
- `project_docs/configuration_ux_redesign/*`

No database, secret, log, backup, virtual environment, cache, `.git` content, SMTP, email, or OTP file belongs in the patch artifact.

