from flask import session

import pytest

from app import app
import flask_app.routes.plc_tag_routes as plc_tag_routes


def test_login_page_has_security_headers():
    app.config.update(TESTING=True)
    with app.test_client() as client:
        response = client.get("/login")

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Cross-Origin-Opener-Policy"] == "same-origin"
    assert response.headers["Cross-Origin-Resource-Policy"] == "same-origin"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    script_policy = next(
        directive
        for directive in response.headers["Content-Security-Policy"].split(";")
        if directive.strip().startswith("script-src")
    )
    assert "'unsafe-inline'" not in script_policy


def test_login_post_without_csrf_is_rejected():
    app.config.update(TESTING=True)
    with app.test_client() as client:
        response = client.post(
            "/login",
            data={"username": "not-a-user", "password": "invalid"},
        )

    assert response.status_code == 400


def test_authenticated_pages_redirect_to_login_when_logged_out():
    app.config.update(TESTING=True)
    with app.test_client() as client:
        response = client.get("/", follow_redirects=False)

    assert response.status_code in {301, 302, 303, 307, 308}
    assert response.headers["Location"].endswith("/login")


def test_operator_cannot_open_engineering_plc_array_routes():
    app.config.update(TESTING=True)
    protected_endpoints = (
        ("array_browser", (1,)),
        ("create_parameter_from_array", (1, 0)),
        ("next_available_index", (1,)),
    )

    with app.test_request_context("/"):
        session["logged_in"] = True
        session["username"] = "test-operator"
        session["role"] = "OPERATOR"

        for endpoint, arguments in protected_endpoints:
            response = app.view_functions[endpoint](*arguments)
            assert response.status_code in {301, 302, 303, 307, 308}
            assert response.headers["Location"].endswith("/")


@pytest.mark.parametrize(
    "endpoint",
    ("array_browser", "next_available_index"),
)
def test_array_routes_redirect_for_scalar_tag(monkeypatch, endpoint):
    monkeypatch.setattr(
        plc_tag_routes.PLCTagManager,
        "get_tag_by_id",
        staticmethod(
            lambda _tag_id: {
                "id": 2,
                "machine_id": 5,
                "stage_id": 11,
                "is_array": 0,
                "array_start_index": None,
                "array_end_index": None,
            }
        ),
    )
    monkeypatch.setattr(
        plc_tag_routes,
        "machine_stage_url",
        lambda *_args, **_kwargs: "/plc-tags/P15/FS",
    )

    with app.test_request_context("/"):
        session.update(logged_in=True, username="admin", role="ADMIN")
        response = app.view_functions[endpoint](2)

    assert response.status_code in {301, 302, 303, 307, 308}
    assert response.headers["Location"].endswith("/plc-tags/P15/FS")
