import os

from flask import request


def _enabled(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def register_security_headers(app):
    """Apply browser-side hardening headers for CRS pages."""

    csp = os.getenv(
        "CRS_CONTENT_SECURITY_POLICY",
        (
            "default-src 'self'; "
            "base-uri 'self'; "
            "object-src 'none'; "
            "frame-ancestors 'none'; "
            "form-action 'self'; "
            "img-src 'self' data:; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; "
            "connect-src 'self'"
        ),
    )

    @app.after_request
    def apply_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
        )
        response.headers.setdefault("Content-Security-Policy", csp)
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")

        if request.is_secure:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )

        if not request.path.startswith("/static/"):
            response.headers.setdefault(
                "Cache-Control",
                "no-store, no-cache, must-revalidate, max-age=0",
            )
            response.headers.setdefault("Pragma", "no-cache")
            response.headers.setdefault("Expires", "0")

        return response


def secure_cookie_enabled():
    """HTTPS-only cookies must be enabled when CRS is served through HTTPS."""
    return _enabled(os.getenv("CRS_COOKIE_SECURE"), default=False)
