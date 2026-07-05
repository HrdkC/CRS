CRS Priority 11 Single Change Cycle - Production Safety Baseline
================================================================

Apply this package on top of Centralized_Recipe_System_Codex_V4_240626.

Main scope:
- Clean professional CSS/JS standardization.
- Login page compact Full HD view without vertical scrolling.
- Final color strategy for status/action buttons.
- Existing active user priority retained.
- Last-login updates only after successful allowed login.
- Browser-close stale session cleanup retained.
- Recipe edit lock manager added.
- PLC buffer operation locks now protect both recipe and PLC resources.
- Audit archive page cleaned and moved to global CSS.
- Flask debug is disabled by default; enable dev debug with CRS_FLASK_DEBUG=1.

Run after copy:
python database\upgrade_user_management_priority11.py
python app.py

For development debug only:
$env:CRS_FLASK_DEBUG = "1"
python app.py

Test pages:
/login
/
/recipes
/stages
/audit-history
/audit-archive
/auto-logout-settings
/active-sessions
/recipe-editor/download-preparation/8

Commit after validation:
git status
git add app.py database flask_app project_docs
git commit -m "Stabilize Priority 11 production safety baseline"
