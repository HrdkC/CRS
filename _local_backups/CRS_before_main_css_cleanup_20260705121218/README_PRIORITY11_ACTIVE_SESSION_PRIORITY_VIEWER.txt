Priority 11 Add-on: Active Session Priority + Viewer Role

Copy database/ and flask_app/ and project_docs/ into project root.
Run:
  python database\upgrade_user_management_priority11.py
  python database\ensure_default_priority11_users.py
  python app.py

Default viewer user:
  viewer / viewer123 / VIEWER

Behavior change:
  Existing active user is not replaced by a second login attempt.
  New login attempt is blocked and logged.
  Active user receives a visible alert with workstation/IP metadata.
