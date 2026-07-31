from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_workflow_mutations_are_post_only_guarded_and_csrf_backed():
    routes = (
        PROJECT_ROOT / "flask_app/routes/configuration_routes.py"
    ).read_text(encoding="utf-8")
    template = (
        PROJECT_ROOT / "flask_app/templates/configuration/setup_workflow.html"
    ).read_text(encoding="utf-8")
    assert '"/configuration/<machine_code>/<stage_code>/setup/progress"' in routes
    assert '"/configuration/<machine_code>/<stage_code>/setup/review"' in routes
    assert routes.count('methods=["POST"]') >= 7
    assert "if not _engineering_config_allowed():" in routes
    assert template.count("<form ") == 3
    assert template.count("{{ csrf_input() }}") == template.count("<form ")
    assert "row_version" in template


def test_parameter_preview_has_no_plc_communication_path():
    service = (
        PROJECT_ROOT / "database/parameter_template_setup_service.py"
    ).read_text(encoding="utf-8")
    preview = service.split("def preview_from_configured_array", 1)[1].split(
        "def get_compatible_template_sources", 1
    )[0]
    assert "LogixDriver" not in preview
    assert ".write(" not in preview
    assert "INSERT INTO" not in preview
    assert "UPDATE " not in preview


def test_second_stage_contract_is_visible_in_guided_workflow():
    template = (
        PROJECT_ROOT / "flask_app/templates/configuration/setup_workflow.html"
    ).read_text(encoding="utf-8")
    assert "CAP_STRIP_SIDE and BT_SIDE only" in template
    assert "Shaping, stop, and position remain PLC-fixed" in template
