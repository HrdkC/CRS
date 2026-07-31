from pathlib import Path

from scripts.build_css_bundle import OUTPUT_PATH, render_bundle


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CSS_ROOT = PROJECT_ROOT / "flask_app" / "static" / "css"
MAIN_CSS = CSS_ROOT / "main.css"
MODULE = CSS_ROOT / "modules" / "34_responsive_header_reflow.css"
BASE_TEMPLATE = PROJECT_ROOT / "flask_app" / "templates" / "base.html"


def test_responsive_header_module_order_and_bundle_are_current():
    manifest = MAIN_CSS.read_text(encoding="utf-8")
    module_text = MODULE.read_text(encoding="utf-8")
    base_template = BASE_TEMPLATE.read_text(encoding="utf-8")

    import_line = (
        '@import url("./modules/34_responsive_header_reflow.css?'
        'v=css-v125-responsive-header-reflow-20260721");'
    )
    assert import_line in manifest
    guided_import = '@import url("./modules/35_parameter_template_guided_setup.css?'
    login_import = '@import url("./modules/36_login_signin_center_alignment.css?'
    workflow_import = '@import url("./modules/37_configuration_workflow.css?'
    action_type_import = (
        '@import url("./modules/38_global_action_typography_standardization.css?'
    )
    assert guided_import in manifest
    assert login_import in manifest
    assert workflow_import in manifest
    assert action_type_import in manifest
    assert (
        manifest.index(import_line)
        < manifest.index(guided_import)
        < manifest.index(login_import)
        < manifest.index(workflow_import)
        < manifest.index(action_type_import)
    )
    assert "@media (max-width: 1180px)" in module_text
    assert "max-height: none !important" in module_text
    assert "overflow: visible !important" in module_text
    assert ".site-header.mobile-navigation-open" in module_text
    assert "css/crs.bundle.css" in base_template
    assert "css-v134-global-action-type-20260731" in base_template
    assert OUTPUT_PATH.read_text(encoding="utf-8") == render_bundle()
