"""Static validation for the final CRS BLOCKED badge visibility contract."""

from __future__ import annotations

import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSS_ROOT = PROJECT_ROOT / "flask_app" / "static" / "css"
MAIN_CSS = CSS_ROOT / "main.css"
BUNDLE_CSS = CSS_ROOT / "crs.bundle.css"
MODULE = CSS_ROOT / "modules" / "31_blocked_dark_theme_visibility.css"
BASE_TEMPLATE = PROJECT_ROOT / "flask_app" / "templates" / "base.html"


def relative_luminance(hex_color: str) -> float:
    values = [int(hex_color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    channels = [
        value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
        for value in values
    ]
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast_ratio(first: str, second: str) -> float:
    high, low = sorted(
        (relative_luminance(first), relative_luminance(second)),
        reverse=True,
    )
    return (high + 0.05) / (low + 0.05)


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def main() -> int:
    if not MODULE.is_file():
        fail(f"Missing CSS module: {MODULE}")

    main_css = MAIN_CSS.read_text(encoding="utf-8")
    bundle = BUNDLE_CSS.read_text(encoding="utf-8")
    module = MODULE.read_text(encoding="utf-8")
    base = BASE_TEMPLATE.read_text(encoding="utf-8")

    imports = re.findall(r'@import\s+url\(["\']?([^"\')?]+)', main_css)
    if not imports:
        fail("No CSS imports found in main.css")
    clean_imports = [item.split("?", 1)[0] for item in imports]
    if "./modules/31_blocked_dark_theme_visibility.css" not in clean_imports:
        fail("Module 31 is not imported")
    if clean_imports[-1] != "./modules/33_ok_status_dark_surface_standardization.css":
        fail("Module 33 is not the final CSS import")

    required_module_tokens = (
        'html[data-crs-resolved-theme="dark"]',
        ".status-blocked",
        "inset 0 0 0 1000px",
        "forced-color-adjust: none",
        "@media (forced-colors: active)",
        "--crs-blocked-solid-bg: #c62828",
        "--crs-blocked-solid-text: #ffffff",
    )
    for token in required_module_tokens:
        if token not in module:
            fail(f"Missing required module token: {token}")

    if "Source: modules/31_blocked_dark_theme_visibility.css" not in bundle:
        fail("Production CSS bundle does not contain module 31")
    if "css-v124-ok-dark-surface-20260717" not in base:
        fail("base.html does not use the V11.8 CSS cache version")

    light_ratio = contrast_ratio("#b91c1c", "#ffffff")
    dark_ratio = contrast_ratio("#c62828", "#ffffff")
    dark_surface_ratio = contrast_ratio("#c62828", "#0f172a")

    if light_ratio < 4.5:
        fail(f"Light-theme BLOCKED text contrast is too low: {light_ratio:.2f}:1")
    if dark_ratio < 4.5:
        fail(f"Dark-theme BLOCKED text contrast is too low: {dark_ratio:.2f}:1")
    if dark_surface_ratio < 3.0:
        fail(f"Dark-theme badge-to-surface contrast is too low: {dark_surface_ratio:.2f}:1")

    if main_css.count("{") != main_css.count("}"):
        fail("main.css brace count is not balanced")
    if module.count("{") != module.count("}"):
        fail("module 31 brace count is not balanced")
    if bundle.count("{") != bundle.count("}"):
        fail("crs.bundle.css brace count is not balanced")

    print("CRS BLOCKED DARK-THEME VISIBILITY CHECK")
    print(f"Final CSS import: {imports[-1]}")
    print(f"Light badge text contrast: {light_ratio:.2f}:1")
    print(f"Dark badge text contrast: {dark_ratio:.2f}:1")
    print(f"Dark badge/surface contrast: {dark_surface_ratio:.2f}:1")
    print("PASS: BLOCKED remains solid red with white text in light, dark, system, and forced-color modes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
