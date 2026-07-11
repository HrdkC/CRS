from flask import session

from app import app


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
