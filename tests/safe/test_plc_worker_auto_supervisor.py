from pathlib import Path


def test_app_starts_supervisor_automatically():
    root = Path(__file__).resolve().parents[2]
    source = (root / "app.py").read_text(encoding="utf-8")
    assert "PLCWorkerSupervisor" in source
    assert "supervisor.start()" in source
    assert "supervisor.stop()" in source
    assert 'CRS_AUTO_START_PLC_WORKER", "1"' in source


def test_production_uses_waitress():
    root = Path(__file__).resolve().parents[2]
    source = (root / "app.py").read_text(encoding="utf-8")
    assert 'DEPLOYMENT_MODE == "production"' in source
    assert "from waitress import serve" in source


def test_worker_supervisor_enables_only_child_process():
    root = Path(__file__).resolve().parents[2]
    source = (root / "utils" / "plc_worker_supervisor.py").read_text(
        encoding="utf-8"
    )
    assert 'child_env["CRS_PLC_WORKER_ENABLED"] = "1"' in source
    assert 'child_env["CRS_ALLOW_PLC_COMMUNICATION"] = "YES"' in source
    assert "subprocess.Popen" in source
    assert "PLCWorkerRuntimeStatus" in source


def test_windows_autostart_has_no_operator_confirmation():
    root = Path(__file__).resolve().parents[2]
    installer = (root / "scripts" / "install_crs_autostart_task.ps1").read_text(
        encoding="utf-8"
    )
    runner = (root / "scripts" / "run_crs_automatic.ps1").read_text(
        encoding="utf-8"
    )
    assert "Read-Host" not in installer
    assert "Read-Host" not in runner
    assert "New-ScheduledTaskTrigger -AtStartup" in installer
    assert '$env:CRS_AUTO_START_PLC_WORKER = "1"' in runner
