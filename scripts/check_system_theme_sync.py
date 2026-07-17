"""Static verification for CRS System theme synchronization assets."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "flask_app" / "templates" / "base.html"
BOOT = ROOT / "flask_app" / "static" / "js" / "theme-bootstrap.js"
MAIN = ROOT / "flask_app" / "static" / "js" / "main.js"
CSS = ROOT / "flask_app" / "static" / "css" / "main.css"
BUNDLE = ROOT / "flask_app" / "static" / "css" / "crs.bundle.css"

checks = {
    "base bootstrap cache version": "js-v119-system-theme-sync-20260717" in BASE.read_text(encoding="utf-8"),
    "base theme-color meta": "crs-theme-color-meta" in BASE.read_text(encoding="utf-8"),
    "bootstrap media query": "prefers-color-scheme: dark" in BOOT.read_text(encoding="utf-8"),
    "bootstrap focus watcher": 'addEventListener("focus"' in BOOT.read_text(encoding="utf-8"),
    "bootstrap visibility watcher": "visibilitychange" in BOOT.read_text(encoding="utf-8"),
    "bootstrap polling fallback": "setInterval" in BOOT.read_text(encoding="utf-8"),
    "main runtime integration": "CRSThemeRuntime" in MAIN.read_text(encoding="utf-8"),
    "system indicator module": "28_system_theme_sync.css" in CSS.read_text(encoding="utf-8"),
    "bundle includes indicator": "28_system_theme_sync.css" in BUNDLE.read_text(encoding="utf-8"),
}

failed = [name for name, ok in checks.items() if not ok]
print("CRS SYSTEM THEME SYNC CHECK")
for name, ok in checks.items():
    print(f"{'PASS' if ok else 'FAIL'}: {name}")
if failed:
    raise SystemExit(1)
print("PASS: System theme synchronization assets are installed.")
