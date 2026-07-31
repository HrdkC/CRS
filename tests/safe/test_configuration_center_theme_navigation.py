from pathlib import Path

from scripts.build_css_bundle import OUTPUT_PATH, render_bundle


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASE_TEMPLATE = PROJECT_ROOT / "flask_app/templates/base.html"
DASHBOARD_TEMPLATE = PROJECT_ROOT / "flask_app/templates/dashboard/dashboard.html"
DASHBOARD_ROUTES = PROJECT_ROOT / "flask_app/routes/dashboard_routes.py"
WORKFLOW_CSS = (
    PROJECT_ROOT
    / "flask_app/static/css/modules/37_configuration_workflow.css"
)


def test_configuration_center_has_one_canonical_navigation_link():
    source = BASE_TEMPLATE.read_text(encoding="utf-8")

    assert source.count('<a href="/configuration">Configuration Center</a>') == 1
    assert '<a href="/configuration">Machine / Stage Readiness</a>' not in source


def test_dashboard_has_one_contextual_setup_action_per_stage():
    template = DASHBOARD_TEMPLATE.read_text(encoding="utf-8")
    routes = DASHBOARD_ROUTES.read_text(encoding="utf-8")

    assert '<a href="/configuration" class="secondary-action">Configuration</a>' not in template
    assert '>Continue Setup</a>' in template
    assert '/{stage_code}/setup"' in routes


def test_configuration_workflow_uses_resolved_dark_theme_contract():
    source = WORKFLOW_CSS.read_text(encoding="utf-8")

    assert 'html[data-crs-resolved-theme="dark"] .configuration-filter-bar' in source
    assert 'html[data-crs-resolved-theme="dark"] .setup-shell' in source
    assert '[data-theme="dark"]' not in source
    assert "var(--crs-dark-surface-2, #132039)" in source


def test_configuration_dark_theme_bundle_and_cache_key_are_current():
    template = BASE_TEMPLATE.read_text(encoding="utf-8")

    assert "css-v134-global-action-type-20260731" in template
    assert OUTPUT_PATH.read_text(encoding="utf-8") == render_bundle()
