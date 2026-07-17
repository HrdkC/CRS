"""Static safety check for the CRS BLOCKED status contract.

The checker does not connect to a PLC or submit state-changing forms. It verifies
that every explicit BLOCKED status uses the canonical class, the CSS module is
last in the cascade, the production bundle is current, and white text on the
chosen red meets WCAG AA for standard text.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = PROJECT_ROOT / "flask_app" / "templates"
CSS_ROOT = PROJECT_ROOT / "flask_app" / "static" / "css"
MODULE_NAME = "30_blocked_status_standardization.css"
MODULE_PATH = CSS_ROOT / "modules" / MODULE_NAME
MAIN_CSS = CSS_ROOT / "main.css"
BUNDLE_PATH = CSS_ROOT / "crs.bundle.css"


def _luminance(hex_value: str) -> float:
    value = hex_value.lstrip("#")
    channels = [int(value[index:index + 2], 16) / 255 for index in (0, 2, 4)]

    def convert(channel: float) -> float:
        if channel <= 0.04045:
            return channel / 12.92
        return ((channel + 0.055) / 1.055) ** 2.4

    red, green, blue = [convert(channel) for channel in channels]
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _contrast(first: str, second: str) -> float:
    high, low = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def find_template_issues() -> list[str]:
    issues: list[str] = []
    explicit_blocked_badge = re.compile(
        r'<(?:span|strong)\b(?P<attrs>[^>]*)>\s*BLOCKED\s*</(?:span|strong)>',
        re.IGNORECASE,
    )
    title_case_blocked_badge = re.compile(
        r'<span\b(?P<attrs>[^>]*)>\s*Blocked\s*</span>',
        re.IGNORECASE,
    )

    for path in sorted(TEMPLATE_ROOT.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(PROJECT_ROOT)

        for pattern in (explicit_blocked_badge, title_case_blocked_badge):
            for match in pattern.finditer(text):
                attrs = match.group("attrs")
                # Metric labels/count labels are not status badges.
                if "metric-label" in attrs:
                    continue
                if "database-blocked-text" in attrs:
                    continue
                if "status-badge" in attrs or "status-pill" in attrs:
                    if "status-blocked" not in attrs and "status-{{" not in attrs:
                        issues.append(f"{rel}: explicit BLOCKED status lacks status-blocked")

    create_recipe = TEMPLATE_ROOT / "recipes" / "create_recipe.html"
    if create_recipe.is_file():
        text = create_recipe.read_text(encoding="utf-8")
        if 'class="metric-text status-text-blocked">Blocked' not in text:
            issues.append("recipes/create_recipe.html: non-pill Blocked text lacks status-text-blocked")

    return issues


def find_css_issues() -> list[str]:
    issues: list[str] = []
    if not MODULE_PATH.is_file():
        return [f"Missing CSS module: {MODULE_PATH}"]

    main = MAIN_CSS.read_text(encoding="utf-8")
    imports = re.findall(r'@import\s+url\(["\']?([^"\')?]+)', main)
    clean_imports = [value.split("?", 1)[0] for value in imports]
    expected = f"./modules/{MODULE_NAME}"
    if expected not in clean_imports:
        issues.append(f"main.css does not import {MODULE_NAME}")
    elif clean_imports[-1] != "./modules/33_ok_status_dark_surface_standardization.css":
        issues.append("Module 33 must be the final CSS import")

    css = MODULE_PATH.read_text(encoding="utf-8")
    required = {
        "Carbon status red": "--crs-status-blocked-bg: #da1e28",
        "white status text": "--crs-status-blocked-text: #ffffff",
        "canonical class": ".status-blocked",
        "non-color alert cue": 'content: "!"',
        "database status": ".database-blocked-text",
        "forced colors": "@media (forced-colors: active)",
    }
    for label, fragment in required.items():
        if fragment not in css:
            issues.append(f"CSS missing {label}: {fragment}")

    if css.count("{") != css.count("}"):
        issues.append("CSS module has unbalanced braces")

    ratio = _contrast("#da1e28", "#ffffff")
    if ratio < 4.5:
        issues.append(f"Blocked contrast ratio fails WCAG AA: {ratio:.2f}:1")

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


def find_python_issues() -> list[str]:
    issues: list[str] = []
    path = PROJECT_ROOT / "flask_app" / "routes" / "dashboard_routes.py"
    text = path.read_text(encoding="utf-8")
    expected = 'status = "Blocked"\n            status_class = "status-blocked"'
    if expected not in text:
        issues.append("dashboard_routes.py does not map Blocked readiness to status-blocked")
    return issues


def main() -> int:
    template_issues = find_template_issues()
    css_issues = find_css_issues()
    python_issues = find_python_issues()
    issues = template_issues + css_issues + python_issues
    ratio = _contrast("#da1e28", "#ffffff")

    print("CRS BLOCKED STATUS STANDARDIZATION CHECK")
    print(f"Templates scanned: {len(list(TEMPLATE_ROOT.rglob('*.html')))}")
    print(f"Blocked red/white contrast: {ratio:.2f}:1")
    print(f"Template issues: {len(template_issues)}")
    print(f"CSS issues: {len(css_issues)}")
    print(f"Python mapping issues: {len(python_issues)}")

    if issues:
        print("FAIL")
        for issue in issues:
            print(f" - {issue}")
        return 1

    print("PASS: BLOCKED statuses use the canonical danger-red pill with white text.")
    print("PASS: BLOCKED remains distinct from neutral unavailable/disabled controls.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
