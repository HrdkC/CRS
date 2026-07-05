Priority 11 Final Safety Closure Fixes - V4.1 to V4.2

Apply after the .gitattributes / clean Git checkpoint steps.

Included fixes:
1. VIEWER is blocked from direct PLC buffer page URL /recipe-editor/download-preparation/<recipe_id>.
2. Recipe edit lock can be explicitly released from the edit page.
3. Browser back/close from edit page sends a best-effort lock release beacon.
4. RecipeResourceLockManager release_session_locks SQL corrected.
5. Same-user blocked login alerts are de-duplicated within 60 seconds and attempt_count is updated.
6. Upgrade script adds attempt_count and last_attempted_at to user_login_attempt_alerts.
7. Upgrade script normalizes SESSION_TIMEOUT_MINUTES to 30 if DB is still using test value <= 5.
8. Campaign carousel documentation updated to final slow timing.

Run:
python database\upgrade_user_management_priority11.py
python app.py

Test:
- Viewer opening /recipe-editor/download-preparation/8 should be blocked and redirected to read-only editor.
- Parameter edit page should show Release Lock & Back and Cancel / Release Lock.
- Same-user repeated login attempts should create one alert with attempt count, not many duplicate cards.
- Auto Logout Settings should show 30 minutes after running upgrade if it was still 5 minutes.
