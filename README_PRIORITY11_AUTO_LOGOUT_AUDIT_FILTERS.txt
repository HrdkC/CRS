CRS Priority 11 Add-on
======================

This package moves Auto Logout Configuration to a separate ADMIN-only page and
adds filters to Audit History.

Copy folders into the project root and overwrite existing files:
- database
- flask_app
- project_docs

Run:
    python database\upgrade_user_management_priority11.py
    python app.py

Key pages:
    /auto-logout-settings
    /active-sessions
    /audit-history
