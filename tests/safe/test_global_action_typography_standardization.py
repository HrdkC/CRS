from pathlib import Path

from scripts.build_css_bundle import OUTPUT_PATH, render_bundle


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CSS_ROOT = PROJECT_ROOT / "flask_app" / "static" / "css"
MAIN_CSS = CSS_ROOT / "main.css"
MODULE = CSS_ROOT / "modules" / "38_global_action_typography_standardization.css"
BASE_TEMPLATE = PROJECT_ROOT / "flask_app" / "templates" / "base.html"
PLC_TEMPLATE = PROJECT_ROOT / "flask_app" / "templates" / "plcs" / "plcs.html"


def test_global_action_module_is_last_and_bundle_is_current():
    manifest = MAIN_CSS.read_text(encoding="utf-8")
    base_template = BASE_TEMPLATE.read_text(encoding="utf-8")

    import_line = (
        '@import url("./modules/38_global_action_typography_standardization.css?'
        'v=css-v134-global-action-type-20260731");'
    )
    assert manifest.rstrip().endswith(import_line)
    assert "css-v134-global-action-type-20260731" in base_template
    assert OUTPUT_PATH.read_text(encoding="utf-8") == render_bundle()


def test_action_groups_use_one_horizontal_row():
    source = MODULE.read_text(encoding="utf-8")

    assert ".row-actions," in source
    assert ".workbench-actions," in source
    assert ".form-action-row," in source
    assert ".setup-actions," in source
    assert "flex-flow: row nowrap !important" in source
    assert "overflow-x: auto" in source
    assert "white-space: nowrap !important" in source
    assert "grid-template-columns: repeat(4, minmax(120px, 1fr)) !important" in source


def test_inline_action_forms_do_not_inherit_card_form_padding():
    source = MODULE.read_text(encoding="utf-8")

    assert ") > form {" in source
    assert "padding: 0 !important" in source
    assert ".plc-registry-actions .row-action-form" in source
    assert ".plc-registry-actions .plc-registry-action-form" in source


def test_plc_registry_actions_have_deterministic_single_row_width():
    source = MODULE.read_text(encoding="utf-8")
    template = PLC_TEMPLATE.read_text(encoding="utf-8")

    assert "width: 410px !important" in source
    assert "width: max-content !important" in source
    assert "min-width: 104px !important" in source
    assert 'class="row-actions plc-registry-actions"' in template
    assert 'class="row-action-form plc-registry-action-form"' in template


def test_page_typography_uses_one_accessible_scale():
    source = MODULE.read_text(encoding="utf-8")

    assert '--crs-page-font-family: "Segoe UI"' in source
    assert "--crs-page-font-body: calc(13px + var(--crs-font-adjust, 0px))" in source
    assert "--crs-page-font-button: calc(12px + var(--crs-font-adjust, 0px))" in source
    assert "--crs-page-font-h1: calc(26px + var(--crs-font-adjust, 0px))" in source
    assert ".site-header" not in source
