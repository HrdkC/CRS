"""Create the private, machine-local Flask signing key used by CRS."""

from __future__ import annotations

import argparse
import os
import secrets
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SECRET_FILE = PROJECT_ROOT / "instance" / "crs_secret_key"


def secret_file_path() -> Path:
    configured = os.getenv("CRS_SECRET_KEY_FILE", "").strip()
    return Path(configured).expanduser() if configured else DEFAULT_SECRET_FILE


def valid_secret(value: str) -> bool:
    return len(value.strip()) >= 43 and value.strip() != "crs_secret_key"


def ensure_secret(force: bool = False) -> tuple[Path, bool]:
    path = secret_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists() and not force:
        existing = path.read_text(encoding="utf-8").strip()
        if not valid_secret(existing):
            raise RuntimeError(
                f"Existing CRS secret file is invalid: {path}. "
                "Use --force only during a controlled session invalidation."
            )
        return path, False

    value = secrets.token_urlsafe(64)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(value + "\n", encoding="utf-8")
    try:
        temporary_path.chmod(0o600)
    except OSError:
        pass
    temporary_path.replace(path)
    return path, True


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Create the private CRS Flask signing key without printing it."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace the key and invalidate all current browser sessions",
    )
    args = parser.parse_args(argv)

    try:
        path, created = ensure_secret(force=args.force)
    except Exception as exc:
        print(f"CRS secret setup failed: {exc}", file=sys.stderr)
        return 1

    state = "created" if created else "already valid"
    print(f"CRS machine-local session secret: {state} ({path})")
    print("Secret value was not displayed and must never be committed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
