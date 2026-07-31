from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.safe
def test_recipe_editor_contains_cross_login_plc_buffer_refresh_contract():
    template = (
        PROJECT_ROOT / "flask_app/templates/recipes/editor.html"
    ).read_text(encoding="utf-8")
    javascript = (
        PROJECT_ROOT / "flask_app/static/js/pages/recipe-editor.js"
    ).read_text(encoding="utf-8")
    routes = (
        PROJECT_ROOT / "flask_app/routes/recipe_editor_routes.py"
    ).read_text(encoding="utf-8")
    guard = (
        PROJECT_ROOT / "flask_app/security/session_guard.py"
    ).read_text(encoding="utf-8")

    assert 'id="plcBufferAction"' in template
    assert 'id="plcBufferBusyStatus"' in template
    assert 'data-refresh-ms="2000"' in template
    assert "can_role_download_recipe" in template

    assert "async function refreshAvailability()" in javascript
    assert 'credentials: "same-origin"' in javascript
    assert 'cache: "no-store"' in javascript
    assert "document.hidden" in javascript
    assert "action.hidden = !available" in javascript

    assert "def recipe_editor_plc_buffer_access_status(recipe_id):" in routes
    assert '"plc_buffer_available": available' in routes
    assert '"operation_active": not available' in routes
    assert '"Cache-Control"] = "no-store, max-age=0"' in routes
    assert '"recipe_editor_plc_buffer_access_status"' in guard


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
def test_plc_buffer_access_endpoint_tracks_shared_operation_lock(monkeypatch):
    from database.recipe_manager import RecipeManager
    from flask_app.routes import recipe_editor_routes

    client = _authenticated_client(monkeypatch)
    monkeypatch.setattr(
        RecipeManager,
        "get_recipe_by_id",
        staticmethod(lambda recipe_id: {"id": recipe_id}),
    )

    monkeypatch.setattr(
        recipe_editor_routes,
        "_active_recipe_operation_lock",
        lambda _recipe_id: {"id": 7, "username": "other_user"},
    )
    busy_response = client.get(
        "/recipe-editor/13/plc-buffer-access-status"
    )
    assert busy_response.status_code == 200
    assert busy_response.get_json()["plc_buffer_available"] is False

    monkeypatch.setattr(
        recipe_editor_routes,
        "_active_recipe_operation_lock",
        lambda _recipe_id: None,
    )
    available_response = client.get(
        "/recipe-editor/13/plc-buffer-access-status"
    )
    assert available_response.status_code == 200
    assert available_response.get_json()["plc_buffer_available"] is True
    assert available_response.headers["Cache-Control"] == "no-store, max-age=0"
