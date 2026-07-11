"""Run CRS through the production WSGI server without venv activation."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _integer_setting(name, default, minimum, maximum):
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(value, maximum))


def runtime_settings():
    mode = os.getenv("CRS_DEPLOYMENT_MODE", "development").strip().lower()
    default_host = "127.0.0.1"
    return {
        "mode": mode,
        "host": os.getenv("CRS_HOST", default_host).strip() or default_host,
        "port": _integer_setting("CRS_PORT", 5000, 1, 65535),
        "threads": _integer_setting("CRS_THREADS", 4, 2, 32),
        "channel_timeout": _integer_setting(
            "CRS_CHANNEL_TIMEOUT_SECONDS",
            120,
            30,
            3600,
        ),
    }


def build_parser():
    parser = argparse.ArgumentParser(
        description="Run CRS using Waitress."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate imports and configuration without starting the server",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    settings = runtime_settings()

    if args.check:
        os.environ.setdefault("CRS_ALLOW_STARTUP_MIGRATIONS", "0")

    try:
        from app import app
    except Exception as exc:
        print(f"CRS startup validation failed: {exc}", file=sys.stderr)
        return 1

    if args.check:
        print("CRS startup validation: OK")
        print(f"Mode: {settings['mode']}")
        print(f"Bind: {settings['host']}:{settings['port']}")
        print(f"Threads: {settings['threads']}")
        return 0

    try:
        from waitress import serve
    except ImportError:
        print(
            "Waitress is not installed. Run setup_crs.bat first.",
            file=sys.stderr,
        )
        return 1

    print(
        "Starting CRS on "
        f"http://{settings['host']}:{settings['port']} "
        f"with {settings['threads']} Waitress threads"
    )
    serve(
        app,
        host=settings["host"],
        port=settings["port"],
        threads=settings["threads"],
        channel_timeout=settings["channel_timeout"],
        clear_untrusted_proxy_headers=True,
        ident="CRS",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
