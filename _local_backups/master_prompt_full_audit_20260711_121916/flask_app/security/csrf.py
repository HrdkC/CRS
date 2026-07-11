import hmac
import secrets
from urllib.parse import urlparse

from flask import (
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
)
from markupsafe import Markup, escape


CSRF_SESSION_KEY = "_csrf_token"
CSRF_FIELD_NAME = "_csrf_token"
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def get_csrf_token():
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def csrf_input():
    return Markup(
        '<input type="hidden" name="{name}" value="{value}">'.format(
            name=CSRF_FIELD_NAME,
            value=escape(get_csrf_token()),
        )
    )


def _request_token():
    return (
        request.form.get(CSRF_FIELD_NAME)
        or request.headers.get("X-CSRFToken")
        or request.headers.get("X-CSRF-Token")
        or ""
    )


def _safe_referrer_path():
    referrer = request.referrer or ""
    if not referrer:
        return None

    parsed_referrer = urlparse(referrer)
    parsed_host = urlparse(request.host_url)
    if parsed_referrer.netloc != parsed_host.netloc:
        return None

    path = parsed_referrer.path or "/"
    if parsed_referrer.query:
        path = f"{path}?{parsed_referrer.query}"
    return path


def _csrf_failure_response():
    message = (
        "Security token expired or missing. Refresh the CRS page and retry the action."
    )

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"ok": False, "error": message}), 400

    if "application/json" in (request.headers.get("Accept") or ""):
        return jsonify({"ok": False, "error": message}), 400

    if session.get("logged_in"):
        flash(message, "warning")
        return redirect(_safe_referrer_path() or "/")

    return (
        render_template(
            "errors/error.html",
            status_code=400,
            title="Security Token Expired",
            message=message,
            technical_detail="CSRF validation failed.",
        ),
        400,
    )


def register_csrf_protection(app):
    """Protect state-changing browser requests with a per-session token."""

    @app.context_processor
    def inject_csrf_helpers():
        return {
            "csrf_token": get_csrf_token,
            "csrf_input": csrf_input,
        }

    @app.before_request
    def validate_csrf_token():
        if request.method not in UNSAFE_METHODS:
            return None

        endpoint = request.endpoint or ""
        if endpoint.startswith("static"):
            return None

        expected = session.get(CSRF_SESSION_KEY)
        supplied = _request_token()
        if expected and supplied and hmac.compare_digest(str(expected), str(supplied)):
            return None

        return _csrf_failure_response()
