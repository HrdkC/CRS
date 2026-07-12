from pathlib import Path

from scripts.build_css_bundle import OUTPUT_PATH, render_bundle


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path):
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_production_css_bundle_is_current_and_has_no_import_chain():
    bundle = OUTPUT_PATH.read_text(encoding="utf-8")
    assert bundle == render_bundle()
    assert "@import" not in bundle


def test_base_uses_local_versioned_progressive_assets():
    base = _read("flask_app/templates/base.html")
    assert "css/crs.bundle.css" in base
    assert "js/vendor/htmx-2.0.10.min.js" in base
    assert "sha384-H5SrcfygHmAuTDZphMHqBJLc3FhssKjG7w/CeCpFReSfwBWDTKpkzPP8c+cLsK+V" in base
    assert "js/theme-bootstrap.js" in base


def test_audit_progressive_region_keeps_get_fallback():
    audit = _read("flask_app/templates/audit/audit_history.html")
    assert 'id="audit-results-region"' in audit
    assert 'hx-target="#audit-results-region"' in audit
    assert 'hx-swap="outerHTML"' in audit
    assert 'method="GET" action="/audit-history"' in audit
    assert 'role="status" aria-live="polite"' in audit


def test_recipe_selector_logic_is_externalized():
    recipes = _read("flask_app/templates/recipes/recipes.html")
    main_js = _read("flask_app/static/js/main.js")
    assert "<script>" not in recipes
    assert "CRS.recipeStageSelector" in main_js


def test_all_template_javascript_is_externalized():
    templates = PROJECT_ROOT / "flask_app" / "templates"
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in templates.rglob("*.html")
    )
    assert "<script>" not in combined
    assert "onclick=" not in combined
    assert "onchange=" not in combined
    assert "onsubmit=" not in combined

    base = _read("flask_app/templates/base.html")
    assert "{% block page_scripts %}{% endblock %}" in base

    expected_modules = (
        "bulk-edit-parameters.js",
        "download-preparation.js",
        "recipe-import-export.js",
    )
    for module in expected_modules:
        assert (PROJECT_ROOT / "flask_app" / "static" / "js" / "pages" / module).is_file()


def test_plc_operation_polling_is_visibility_aware_and_terminal_driven():
    script = _read("flask_app/static/js/pages/download-preparation.js")
    assert 'document.addEventListener("visibilitychange"' in script
    assert "pollInFlight" in script
    assert "schedulePoll" in script
    assert "Status connection interrupted" in script
