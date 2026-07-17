"""Validate CRS OK status and remaining dark-theme page coverage.

Safe static check: no PLC connection or PLC write is performed.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSS_ROOT = PROJECT_ROOT / "flask_app" / "static" / "css"
TEMPLATE_ROOT = PROJECT_ROOT / "flask_app" / "templates"
MODULE = CSS_ROOT / "modules" / "33_ok_status_dark_surface_standardization.css"
MAIN = CSS_ROOT / "main.css"
BUNDLE = CSS_ROOT / "crs.bundle.css"
BASE = TEMPLATE_ROOT / "base.html"


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
        module_source = ""
    else:
        module_source = MODULE.read_text(encoding="utf-8")

    main_source = MAIN.read_text(encoding="utf-8")
    imports = re.findall(r'@import\s+url\(["\']?([^"\')?]+)', main_source)
    clean_imports = [item.split("?", 1)[0] for item in imports]
    expected = "./modules/33_ok_status_dark_surface_standardization.css"
    if not clean_imports or clean_imports[-1] != expected:
        errors.append("Module 33 must be the final CSS import")

    required_css = {
        "OK green": "--crs-status-ok-bg: #166534",
        "OK white text": "--crs-status-ok-text: #ffffff",
        "canonical OK class": ".status-ok",
        "OK check cue": 'content: "✓"',
        "PLC browser dark coverage": ".plc-browser-v2",
        "bulk editor dark coverage": ".bulk-edit-control-bar",
        "buffer page dark coverage": ".buffer-panel",
        "live status dark coverage": ".live-status-item",
        "forced colors": "@media (forced-colors: active)",
    }
    for label, token in required_css.items():
        if token not in module_source:
            errors.append(f"Missing {label}: {token}")

    if module_source.count("{") != module_source.count("}"):
        errors.append("Module 33 has unbalanced braces")

    base_source = BASE.read_text(encoding="utf-8")
    if "css-v124-ok-dark-surface-20260717" not in base_source:
        errors.append("base.html does not use the V11.10 cache version")

    # Exact OK labels must use status-ok, not generic status-success.
    legacy_ok = re.compile(
        r'class="[^"]*status-success[^"]*"[^>]*>\s*OK\s*<',
        re.IGNORECASE | re.DOTALL,
    )
    for path in TEMPLATE_ROOT.rglob("*.html"):
        source = path.read_text(encoding="utf-8", errors="replace")
        if legacy_ok.search(source):
            errors.append(
                f"Legacy status-success OK in {path.relative_to(PROJECT_ROOT).as_posix()}"
            )

    # Audit hard-coded light backgrounds in template style blocks. They are
    # accepted only where module 33 explicitly supplies a dark-mode override.
    light_background = re.compile(
        r'background(?:-color)?\s*:\s*[^;\n}]*(?:#fff(?:fff)?\b|#f8fafc\b|'
        r'#f1f5f9\b|#eff6ff\b|#f0f9ff\b|#fffbeb\b|#fef2f2\b|'
        r'#eef2f7\b|#faf5ff\b|\bwhite\b)',
        re.IGNORECASE,
    )
    style_block = re.compile(r"<style[^>]*>(.*?)</style>", re.IGNORECASE | re.DOTALL)
    covered = {
        "flask_app/templates/plc_tags/browser.html": [".plc-browser-v2"],
        "flask_app/templates/recipes/bulk_edit_parameters.html": [".bulk-edit-control-bar"],
        "flask_app/templates/recipes/download_preparation.html": [
            ".buffer-panel",
            ".live-status-item",
            ".step-item",
            ".compact-details",
            ".operation-lock-warning",
        ],
    }
    for path in TEMPLATE_ROOT.rglob("*.html"):
        source = path.read_text(encoding="utf-8", errors="replace")
        blocks = style_block.findall(source)
        if not any(light_background.search(block) for block in blocks):
            continue
        rel = path.relative_to(PROJECT_ROOT).as_posix()
        markers = covered.get(rel)
        if not markers:
            errors.append(f"Uncovered template light-style block: {rel}")
            continue
        for marker in markers:
            if marker not in module_source:
                errors.append(f"Dark override marker missing for {rel}: {marker}")

    light_ratio = contrast("#166534", "#ffffff")
    dark_ratio = contrast("#15803d", "#ffffff")
    dark_surface_ratio = contrast("#15803d", "#0f1a2e")
    if light_ratio < 4.5:
        errors.append(f"Light-theme OK text contrast below 4.5:1: {light_ratio:.2f}:1")
    if dark_ratio < 4.5:
        errors.append(f"Dark-theme OK text contrast below 4.5:1: {dark_ratio:.2f}:1")
    if dark_surface_ratio < 3.0:
        errors.append(
            f"Dark-theme OK badge/surface contrast below 3.0:1: {dark_surface_ratio:.2f}:1"
        )

    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "build_css_bundle.py"), "--check"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        errors.append(result.stdout.strip() or result.stderr.strip() or "CSS bundle is stale")

    print("CRS OK STATUS + DARK SURFACE CHECK")
    print(f"CSS modules: {len(imports)}")
    print(f"Light OK text contrast: {light_ratio:.2f}:1")
    print(f"Dark OK text contrast: {dark_ratio:.2f}:1")
    print(f"Dark OK badge/surface contrast: {dark_surface_ratio:.2f}:1")

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1

    print("PASS: OK uses green background, white text and check cue in light/dark themes.")
    print("PASS: Known template-local light surfaces have final dark-theme coverage.")
    print("PASS: Production CSS bundle is current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
