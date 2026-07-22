from pathlib import Path

from config import settings


def test_restore_delay_and_auto_worker_settings_coexist():
    assert settings.PLC_RESTORE_VERIFY_DELAY_SECONDS >= 0.2
    assert hasattr(settings, "AUTO_START_PLC_WORKER")
    assert settings.PLC_WORKER_POLL_SECONDS > 0


def test_plc_buffer_manager_has_partial_patch_compatibility_guard():
    manager_path = (
        Path(__file__).resolve().parents[2]
        / "database"
        / "plc_buffer_operation_manager.py"
    )
    source = manager_path.read_text(encoding="utf-8")
    assert "from config.settings import PLC_RESTORE_VERIFY_DELAY_SECONDS" in source
    assert "except ImportError" in source
    assert "CRS_PLC_RESTORE_VERIFY_DELAY_SECONDS" in source
