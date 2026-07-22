from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.safe
def test_download_preparation_dark_theme_and_live_refresh_contract():
    template = (
        PROJECT_ROOT / "flask_app" / "templates" / "recipes" / "download_preparation.html"
    ).read_text(encoding="utf-8")
    javascript = (
        PROJECT_ROOT / "flask_app" / "static" / "js" / "pages" / "download-preparation.js"
    ).read_text(encoding="utf-8")
    routes = (
        PROJECT_ROOT / "flask_app" / "routes" / "recipe_editor_routes.py"
    ).read_text(encoding="utf-8")
    guard = (
        PROJECT_ROOT / "flask_app" / "security" / "session_guard.py"
    ).read_text(encoding="utf-8")

    assert 'id="livePlcStatusPanel"' in template
    assert 'data-refresh-ms="2000"' in template
    assert 'id="liveStatusRefreshButton"' in template
    assert 'id="liveStatusIssuesList"' in template
    assert 'data-live-purpose="{{ item.purpose }}"' in template
    assert 'html[data-crs-resolved-theme="dark"] .buffer-panel' in template
    assert '.machine-stage-tag-panel .tag-chip' in template

    assert 'function fetchLiveStatus(manualRefresh)' in javascript
    assert 'credentials: "same-origin"' in javascript
    assert 'cache: "no-store"' in javascript
    assert 'document.hidden' in javascript
    assert 'live-status-item-' in javascript

    assert 'def recipe_download_preparation_live_status(recipe_id):' in routes
    assert 'PLCBufferOperationManager.get_live_tag_status' in routes
    assert 'Cache-Control' in routes
    assert '"recipe_download_preparation_live_status"' in guard


def _authenticated_client(monkeypatch):
    import time

    from app import app
    from database.user_session_manager import UserSessionManager

    monkeypatch.setattr(
        UserSessionManager,
        "close_expired_and_stale_sessions",
        staticmethod(lambda **_kwargs: 0),
    )
    monkeypatch.setattr(
        UserSessionManager,
        "is_session_active",
        staticmethod(lambda *_args, **_kwargs: True),
    )
    monkeypatch.setattr(
        UserSessionManager,
        "get_session_authority",
        staticmethod(lambda *_args, **_kwargs: {
            "active": 1,
            "current_role": "ADMIN",
            "password_reset_required": 0,
        }),
    )
    monkeypatch.setattr(
        UserSessionManager,
        "heartbeat",
        staticmethod(lambda *_args, **_kwargs: None),
    )
    monkeypatch.setattr(
        UserSessionManager,
        "get_pending_login_attempt_alerts",
        staticmethod(lambda *_args, **_kwargs: []),
    )

    app.config.update(TESTING=True)
    client = app.test_client()
    now = int(time.time())
    with client.session_transaction() as session:
        session.update(
            logged_in=True,
            username="admin",
            role="ADMIN",
            session_id=999999,
            last_activity_epoch=now,
            last_db_touch_epoch=now,
            password_reset_required=0,
        )
    return client


@pytest.mark.safe
def test_live_status_endpoint_returns_json_without_cache_or_plc_access(monkeypatch):
    from database.plc_buffer_operation_manager import PLCBufferOperationManager
    from database.recipe_manager import RecipeManager

    client = _authenticated_client(monkeypatch)
    monkeypatch.setattr(
        RecipeManager,
        "get_recipe_by_id",
        staticmethod(lambda _recipe_id: {"id": 13, "machine_id": 1, "stage_id": 1}),
    )
    monkeypatch.setattr(
        PLCBufferOperationManager,
        "get_live_tag_status",
        staticmethod(lambda **_kwargs: {
            "connected": True,
            "status": "READY",
            "summary": "All readable live PLC interlocks are healthy.",
            "issues": [],
            "groups": [{
                "title": "Interlocks",
                "items": [{
                    "purpose": "DOWNLOAD_ENABLE",
                    "label": "Download enable",
                    "tag": {"tag_name": "CRS_Download_Enable"},
                    "value": True,
                    "expected_text": "TRUE",
                    "status": "ok",
                    "status_text": "Healthy",
                    "message": "Good to go.",
                }],
            }],
        }),
    )

    response = client.get(
        "/recipe-editor/download-preparation/13/live-status?plc_id=6"
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["live_status"]["connected"] is True
    assert payload["live_status"]["groups"][0]["items"][0]["value"] is True
    assert response.headers["Cache-Control"] == "no-store, max-age=0"
