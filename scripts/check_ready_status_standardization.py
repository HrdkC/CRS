"""Validate the final CRS READY status contract."""

from __future__ import annotations

import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSS_ROOT = PROJECT_ROOT / "flask_app" / "static" / "css"
TEMPLATE_ROOT = PROJECT_ROOT / "flask_app" / "templates"
MODULE = CSS_ROOT / "modules" / "32_ready_status_standardization.css"
MAIN = CSS_ROOT / "main.css"
BASE = TEMPLATE_ROOT / "base.html"
DASHBOARD_ROUTES = PROJECT_ROOT / "flask_app" / "routes" / "dashboard_routes.py"


def luminance(hex_color: str) -> float:
    value = hex_color.lstrip("#")
    channels = [int(value[index:index + 2], 16) / 255 for index in (0, 2, 4)]

    def linear(channel: float) -> float:
        return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4

    red, green, blue = [linear(channel) for channel in channels]
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast(first: str, second: str) -> float:
    high, low = sorted((luminance(first), luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def main() -> int:
    errors: list[str] = []

    if not MODULE.is_file():
        errors.append(f"Missing module: {MODULE}")
    else:
        css = MODULE.read_text(encoding="utf-8")
        required = [
            "--crs-status-ready-bg: #15803d",
            "--crs-status-ready-text: #ffffff",
            ".status-ready",
            "content: \"✓\"",
            "data-crs-resolved-theme=\"dark\"",
            "forced-colors: active",
        ]
        for token in required:
            if token not in css:
                errors.append(f"READY CSS token missing: {token}")

    manifest = MAIN.read_text(encoding="utf-8")
    imports = re.findall(r'@import\s+url\(["\']?([^"\')?]+)', manifest)
    clean_imports = [item.split("?", 1)[0] for item in imports]
    if "./modules/32_ready_status_standardization.css" not in clean_imports:
        errors.append("READY module is not imported")
    if not clean_imports or clean_imports[-1] != "./modules/33_ok_status_dark_surface_standardization.css":
        errors.append("Final CRS semantic/theme module is not module 33")

    base = BASE.read_text(encoding="utf-8")
    if "css-v124-ok-dark-surface-20260717" not in base:
        errors.append("base.html does not use the READY cache version")

    # READY text must not use generic success/warning/danger styling.
    bad_pattern = re.compile(
        r'class="[^"]*status-(?:success|warning|danger|blocked)[^"]*"[^>]*>\s*'
        r'(?:READY|Ready|Tag Ready|Ready To Import)\s*<',
        re.IGNORECASE,
    )
    for path in TEMPLATE_ROOT.rglob("*.html"):
        text = path.read_text(encoding="utf-8", errors="replace")
        if bad_pattern.search(text):
            errors.append(f"Non-standard READY class in {path.relative_to(PROJECT_ROOT)}")

    dashboard = DASHBOARD_ROUTES.read_text(encoding="utf-8")
    if 'status = "Ready"' not in dashboard or 'status_class = "status-ready"' not in dashboard:
        errors.append("Dashboard machine/stage readiness does not use status-ready")

    text_contrast = contrast("#15803d", "#ffffff")
    dark_surface_contrast = contrast("#15803d", "#101a2d")
    if text_contrast < 4.5:
        errors.append(f"READY white-text contrast is below 4.5:1: {text_contrast:.2f}:1")
    if dark_surface_contrast < 3.0:
        errors.append(
            f"READY badge/dark-surface contrast is below 3.0:1: {dark_surface_contrast:.2f}:1"
        )

    print("CRS READY STATUS STANDARDIZATION CHECK")
    print(f"White text contrast: {text_contrast:.2f}:1")
    print(f"Dark badge/surface contrast: {dark_surface_contrast:.2f}:1")

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1

    print("PASS: READY uses a green background, white text and check mark in light and dark themes.")
    print("PASS: READY semantics are standardized across templates and dashboard readiness.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
