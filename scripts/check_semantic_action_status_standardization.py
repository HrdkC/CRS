"""Check CRS semantic action and status color standardization.

This checker is intentionally static and safe: it does not connect to PLCs or
submit any state-changing form. It verifies template semantics, CSS import
order, and the generated production CSS bundle.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = PROJECT_ROOT / "flask_app" / "templates"
CSS_ROOT = PROJECT_ROOT / "flask_app" / "static" / "css"
MODULE_NAME = "29_semantic_action_status_standardization.css"
MODULE_PATH = CSS_ROOT / "modules" / MODULE_NAME
MAIN_CSS = CSS_ROOT / "main.css"
BUNDLE_PATH = CSS_ROOT / "crs.bundle.css"


def template_files() -> list[Path]:
    return sorted(TEMPLATE_ROOT.rglob("*.html"))


def find_template_issues() -> list[str]:
    issues: list[str] = []

    disabled_neutral = re.compile(
        r'class="[^"]*status-neutral[^"]*"[^>]*>\s*Disabled\s*<',
        re.IGNORECASE,
    )
    active_wrong = re.compile(
        r'class="(?P<classes>[^"]*status-badge[^"]*)"[^>]*>\s*Active\s*<',
        re.IGNORECASE,
    )
    disable_form = re.compile(
        r'<form\b[^>]*action="[^"]*/disable(?:/|\")[\s\S]*?</form>',
        re.IGNORECASE,
    )
    enable_form = re.compile(
        r'<form\b[^>]*action="[^"]*/enable(?:/|\")[\s\S]*?</form>',
        re.IGNORECASE,
    )

    for path in template_files():
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(PROJECT_ROOT)

        if disabled_neutral.search(text):
            issues.append(f"{rel}: Disabled status still uses status-neutral")

        for match in active_wrong.finditer(text):
            classes = set(match.group("classes").split())
            if not {"status-success", "status-active"}.issubset(classes):
                issues.append(
                    f"{rel}: Active status must include status-success and status-active"
                )

        for block in disable_form.findall(text):
            if "action-disable" not in block and " danger" not in block and " disable" not in block:
                issues.append(
                    f"{rel}: /disable form lacks action-disable/danger semantic class"
                )

        for block in enable_form.findall(text):
            if "action-enable" not in block and " success" not in block and " enable" not in block:
                issues.append(
                    f"{rel}: /enable form lacks action-enable/success semantic class"
                )

    return issues


def find_css_issues() -> list[str]:
    issues: list[str] = []

    if not MODULE_PATH.is_file():
        return [f"Missing CSS module: {MODULE_PATH}"]

    main = MAIN_CSS.read_text(encoding="utf-8")
    imports = re.findall(r'@import\s+url\(["\']?([^"\')?]+)', main)
    clean_imports = [item.split("?", 1)[0] for item in imports]
    expected = f"./modules/{MODULE_NAME}"

    if expected not in clean_imports:
        issues.append(f"main.css does not import {MODULE_NAME}")
    else:
        module_index = clean_imports.index(expected)
        required_tail = [
            "./modules/30_blocked_status_standardization.css",
            "./modules/31_blocked_dark_theme_visibility.css",
            "./modules/32_ready_status_standardization.css",
            "./modules/33_ok_status_dark_surface_standardization.css",
        ]
        if clean_imports[module_index + 1:] != required_tail:
            issues.append(
                f"{MODULE_NAME} must be followed by the dedicated semantic/theme modules 30-33"
            )

    css = MODULE_PATH.read_text(encoding="utf-8")
    required_fragments = {
        "disable red": "--crs-action-disable-bg: #dc2626",
        "enable green": "--crs-action-enable-bg: #15803d",
        "white text": "-webkit-text-fill-color: #ffffff",
        "disable semantic class": ".action-disable",
        "enable semantic class": ".action-enable",
        "disabled status": ".status-disabled",
        "active status": ".status-active",
        "unavailable neutral": "--crs-unavailable-bg: #475569",
    }
    for label, fragment in required_fragments.items():
        if fragment not in css:
            issues.append(f"CSS module missing {label}: {fragment}")

    if css.count("{") != css.count("}"):
        issues.append("CSS module has unbalanced braces")

    if not BUNDLE_PATH.is_file():
        issues.append("Production CSS bundle is missing")
    else:
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "build_css_bundle.py"), "--check"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            issues.append(result.stdout.strip() or result.stderr.strip() or "CSS bundle is stale")

    return issues


def main() -> int:
    template_issues = find_template_issues()
    css_issues = find_css_issues()
    issues = template_issues + css_issues

    print("CRS SEMANTIC ACTION / STATUS STANDARDIZATION CHECK")
    print(f"Templates scanned: {len(template_files())}")
    print(f"Template issues: {len(template_issues)}")
    print(f"CSS issues: {len(css_issues)}")

    if issues:
        print("FAIL")
        for issue in issues:
            print(f" - {issue}")
        return 1

    print("PASS: Disable actions/statuses are red with white text; Enable/Active are green with white text.")
    print("PASS: Truly unavailable controls use neutral readable styling, not white-on-white.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
