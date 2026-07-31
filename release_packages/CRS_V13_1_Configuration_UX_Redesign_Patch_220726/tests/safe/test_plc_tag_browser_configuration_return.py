from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.safe
def test_plc_tag_browser_has_page_level_configuration_return_navigation():
    route_source = (
        PROJECT_ROOT / "flask_app" / "routes" / "plc_tag_routes.py"
    ).read_text(encoding="utf-8")
    template_source = (
        PROJECT_ROOT / "flask_app" / "templates" / "plc_tags" / "browser.html"
    ).read_text(encoding="utf-8")

    assert 'configuration_readiness_url=(' in route_source
    assert '"/setup?step=plc_tags" if purpose_to_assign else ""' in route_source
    assert "{% if purpose_to_assign %}" in template_source
    assert "Back to Configuration" in template_source
    assert "configuration_readiness_url" in template_source
    assert "Return to Configuration Readiness for this machine and stage." in template_source
