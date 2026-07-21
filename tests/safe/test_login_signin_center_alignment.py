from pathlib import Path

from scripts.build_css_bundle import OUTPUT_PATH, render_bundle


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CSS_ROOT = PROJECT_ROOT / "flask_app" / "static" / "css"
MAIN_CSS = CSS_ROOT / "main.css"
MODULE = CSS_ROOT / "modules" / "36_login_signin_center_alignment.css"
BASE_TEMPLATE = PROJECT_ROOT / "flask_app" / "templates" / "base.html"
LOGIN_TEMPLATE = PROJECT_ROOT / "flask_app" / "templates" / "auth" / "login.html"


def test_login_signin_center_module_is_last_and_bundle_is_current():
    manifest = MAIN_CSS.read_text(encoding="utf-8")
    module_text = MODULE.read_text(encoding="utf-8")
    base_template = BASE_TEMPLATE.read_text(encoding="utf-8")
    login_template = LOGIN_TEMPLATE.read_text(encoding="utf-8")

    assert manifest.rstrip().endswith(
        '@import url("./modules/36_login_signin_center_alignment.css?'
        'v=css-v127-login-signin-center-20260721");'
    )
    assert ".compact-corporate-login-panel .compact-login-form" in module_text
    assert "justify-self: center !important" in module_text
    assert ".compact-corporate-login-panel .login-submit-button" in module_text
    assert "justify-content: center !important" in module_text
    assert "text-align: center !important" in module_text
    assert "margin: 10px auto 0 !important" in module_text
    assert "css-v127-login-signin-center-20260721" in base_template
    assert 'class="login-submit-button">Sign In</button>' in login_template
    assert OUTPUT_PATH.read_text(encoding="utf-8") == render_bundle()
