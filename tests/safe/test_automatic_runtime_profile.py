from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_automatic_runner_uses_waitress_without_forcing_production_security():
    text = (ROOT / "scripts" / "run_crs_automatic.ps1").read_text(
        encoding="utf-8"
    )
    assert '"development"' in text
    assert "$env:CRS_USE_WAITRESS" in text
    assert '"1"' in text
    assert '$env:CRS_AUTO_START_PLC_WORKER = "1"' in text


def test_app_separates_waitress_from_security_mode():
    text = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "def should_use_waitress" in text
    assert 'deployment_mode == "production"' in text
    assert '"CRS_USE_WAITRESS"' in text
    assert "if use_waitress:" in text


def test_task_ignores_duplicate_start_request():
    text = (ROOT / "scripts" / "install_crs_autostart_task.ps1").read_text(
        encoding="utf-8"
    )
    assert "-MultipleInstances IgnoreNew" in text
    assert "-NonInteractive" in text
