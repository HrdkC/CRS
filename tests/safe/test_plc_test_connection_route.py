import os
import time
from types import SimpleNamespace

os.environ.setdefault("CRS_ALLOW_STARTUP_MIGRATIONS", "0")

from app import app
from database.plc_registry_manager import PLCRegistryManager
from database.user_session_manager import UserSessionManager
import flask_app.routes.plc_routes as plc_routes


def _authenticated_client(monkeypatch):
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
        "touch",
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


def test_plc_connection_page_handles_offline_controller(monkeypatch):
    client = _authenticated_client(monkeypatch)
    monkeypatch.setattr(
        PLCRegistryManager,
        "get_plc_by_id",
        staticmethod(
            lambda _plc_id: {
                "id": 1,
                "plc_name": "P01_FS_PLC",
                "ip_address": "172.20.56.131",
            }
        ),
    )
    monkeypatch.setattr(
        plc_routes.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=1),
    )

    response = client.get("/plcs/test_connection/1")

    assert response.status_code == 200
    assert b"P01_FS_PLC" in response.data
    assert b"OFFLINE" in response.data


def test_plc_connection_page_redirects_for_missing_record(monkeypatch):
    client = _authenticated_client(monkeypatch)
    monkeypatch.setattr(
        PLCRegistryManager,
        "get_plc_by_id",
        staticmethod(lambda _plc_id: None),
    )

    response = client.get("/plcs/test_connection/999999")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/plcs")
