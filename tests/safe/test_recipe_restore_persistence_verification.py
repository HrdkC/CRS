import pytest

from database.plc_buffer_operation_manager import PLCBufferOperationManager
from database.recipe_parameter_value_manager import RecipeParameterValueManager


class _FakeConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _base_result():
    result = PLCBufferOperationManager.make_result("recipe_restore")
    result["recipe"] = {"id": 13, "recipe_code": "TEST_P01FS"}
    result["plc"] = {"ip_address": "127.0.0.1"}
    result["payload_size"] = 3
    return result


def _install_common_mocks(monkeypatch, readbacks):
    monkeypatch.setattr(
        RecipeParameterValueManager,
        "get_recipe_values",
        staticmethod(
            lambda recipe_id: [
                {
                    "plc_array_index": 0,
                    "parameter_value": 11.0,
                    "minimum_value": 0.0,
                    "maximum_value": 100.0,
                },
                {
                    "plc_array_index": 1,
                    "parameter_value": 0.0,
                    "minimum_value": 0.0,
                    "maximum_value": 100.0,
                },
                {
                    "plc_array_index": 2,
                    "parameter_value": 0.0,
                    "minimum_value": 0.0,
                    "maximum_value": 100.0,
                },
            ]
        ),
    )
    monkeypatch.setattr(
        PLCBufferOperationManager,
        "require_array_tag",
        staticmethod(lambda *args, **kwargs: {"tag_name": "CRS_Recipe_Data"}),
    )
    monkeypatch.setattr(
        PLCBufferOperationManager,
        "get_tag_for_purpose",
        staticmethod(lambda *args, **kwargs: None),
    )
    monkeypatch.setattr(
        PLCBufferOperationManager,
        "validate_payload_or_block",
        staticmethod(lambda *args, **kwargs: None),
    )
    monkeypatch.setattr(
        PLCBufferOperationManager,
        "write_or_block",
        staticmethod(lambda *args, **kwargs: None),
    )
    monkeypatch.setattr(
        PLCBufferOperationManager,
        "write_phase_control_arrays",
        staticmethod(lambda *args, **kwargs: None),
    )
    monkeypatch.setattr(
        PLCBufferOperationManager,
        "read_array_or_block",
        staticmethod(lambda *args, **kwargs: readbacks.pop(0)),
    )
    monkeypatch.setattr(
        "database.plc_buffer_operation_manager.LogixDriver",
        lambda *args, **kwargs: _FakeConnection(),
    )
    monkeypatch.setattr(
        "database.plc_buffer_operation_manager.time.sleep",
        lambda seconds: None,
    )


def test_restore_succeeds_only_when_value_persists(monkeypatch):
    _install_common_mocks(
        monkeypatch,
        readbacks=[[11.0, 0.0, 0.0], [11.0, 0.0, 0.0]],
    )

    result = PLCBufferOperationManager.restore_recipe_to_crs_buffer(_base_result())

    assert result["success"] is True
    assert result["persistent_payload_compare"]["matched"] is True
    assert result["metrics"]["restore_persistent_preview"][0] == 11.0


def test_restore_is_blocked_when_plc_overwrites_value_after_write(monkeypatch):
    result = _base_result()
    _install_common_mocks(
        monkeypatch,
        readbacks=[[11.0, 0.0, 0.0], [0.0, 0.0, 0.0]],
    )

    with pytest.raises(Exception, match="did not retain the restored values"):
        PLCBufferOperationManager.restore_recipe_to_crs_buffer(result)

    assert result["success"] is False
    assert result["persistent_payload_compare"]["matched"] is False
    assert "Index 0: expected 11.0, actual 0.0" in result["errors"][-1]
