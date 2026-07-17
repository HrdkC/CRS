"""Static CRS dark-theme completion check.

This check is safe: it does not connect to or write any PLC. It verifies that the
final dark-theme module is imported last, the production CSS bundle is current,
important page components are covered, and templates do not contain inline white
backgrounds that bypass the theme layer.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSS_ROOT = PROJECT_ROOT / "flask_app" / "static" / "css"
TEMPLATE_ROOT = PROJECT_ROOT / "flask_app" / "templates"
MAIN_CSS = CSS_ROOT / "main.css"
BUNDLE_CSS = CSS_ROOT / "crs.bundle.css"
FINAL_MODULE = CSS_ROOT / "modules" / "33_ok_status_dark_surface_standardization.css"
BASE_TEMPLATE = TEMPLATE_ROOT / "base.html"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

IMPORT_RE = re.compile(r'@import\s+url\(["\']?([^"\')?]+)')
INLINE_LIGHT_RE = re.compile(
    r'style=["\'][^"\']*(?:background|background-color)\s*:[^;"\']*'
    r'(?:#fff(?:fff)?\b|\bwhite\b|rgb\(\s*255\s*,\s*255\s*,\s*255)',
    re.IGNORECASE,
)

REQUIRED_MARKERS = {
    "OK status": ".status-ok",
    "PLC browser surfaces": ".plc-browser-v2",
    "bulk editor surface": ".bulk-edit-control-bar",
    "buffer operation surface": ".buffer-panel",
}


def fail(message: str) -> int:
    print(f"FAIL: {message}")
    return 1


def main() -> int:
    if not MAIN_CSS.is_file() or not FINAL_MODULE.is_file() or not BUNDLE_CSS.is_file():
        return fail("Required CSS entry, final module, or production bundle is missing.")

    main_source = MAIN_CSS.read_text(encoding="utf-8")
    imports = IMPORT_RE.findall(main_source)
    if not imports:
        return fail("No CSS module imports found in main.css.")

    last_import = imports[-1].split("?", 1)[0]
    if not last_import.endswith("modules/33_ok_status_dark_surface_standardization.css"):
        return fail(f"Final dark-theme module is not imported last: {last_import}")

    module_source = FINAL_MODULE.read_text(encoding="utf-8")
    if module_source.count("{") != module_source.count("}"):
        return fail("27_dark_theme_complete.css has unbalanced braces.")

    missing_markers = [name for name, marker in REQUIRED_MARKERS.items() if marker not in module_source]
    if missing_markers:
        return fail("Missing dark-theme coverage markers: " + ", ".join(missing_markers))

    # Use the existing official builder so this check cannot disagree with production.
    from scripts.build_css_bundle import render_bundle

    expected_bundle = render_bundle()
    actual_bundle = BUNDLE_CSS.read_text(encoding="utf-8")
    if actual_bundle != expected_bundle:
        return fail("crs.bundle.css is stale. Run: python scripts/build_css_bundle.py")

    base_source = BASE_TEMPLATE.read_text(encoding="utf-8")
    if "css-v124-ok-dark-surface-20260717" not in base_source:
        return fail("base.html does not use the V11.8 dark-theme cache version.")

    inline_violations = []
    template_count = 0
    for template in TEMPLATE_ROOT.rglob("*.html"):
        template_count += 1
        source = template.read_text(encoding="utf-8", errors="replace")
        if INLINE_LIGHT_RE.search(source):
            inline_violations.append(template.relative_to(PROJECT_ROOT).as_posix())

    if inline_violations:
        return fail("Inline light backgrounds found in templates: " + ", ".join(inline_violations))

    print("CRS DARK THEME COVERAGE CHECK")
    print(f"Templates scanned: {template_count}")
    print(f"CSS modules: {len(imports)}")
    print("Final module: modules/33_ok_status_dark_surface_standardization.css")
    print("Production bundle: current")
    print("Inline white template backgrounds: 0")
    print("PASS: Complete dark-theme override layer is installed and bundled.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
