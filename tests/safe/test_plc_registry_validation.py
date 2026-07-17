import pytest

import database.plc_registry_manager as plc_registry_module
from database.plc_registry_manager import PLCRegistryManager


@pytest.mark.parametrize(
    "value, expected",
    [
        ("172.20.56.169", "172.20.56.169"),
        (" 10.0.0.8 ", "10.0.0.8"),
        ("2001:db8::10", "2001:db8::10"),
    ],
)
def test_plc_ip_validation_accepts_valid_unicast_addresses(value, expected):
    assert PLCRegistryManager.validate_ip_address(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "",
        "not-an-ip",
        "127.0.0.1",
        "0.0.0.0",
        "224.0.0.1",
        "-n 10.0.0.1",
    ],
)
def test_plc_ip_validation_rejects_unsafe_addresses(value):
    with pytest.raises(ValueError):
        PLCRegistryManager.validate_ip_address(value)


class _FakeCursor:
    def __init__(self, row):
        self.row = row
        self.parameters = None

    def execute(self, _query, parameters):
        self.parameters = parameters

    def fetchone(self):
        return self.row


class _FakeConnection:
    def __init__(self, row):
        self.cursor_instance = _FakeCursor(row)
        self.closed = False

    def cursor(self):
        return self.cursor_instance

    def close(self):
        self.closed = True


@pytest.mark.parametrize(
    "row, expected",
    [
        ({"id": 7, "plc_name": "P15_FS_PLC"}, {"id": 7, "plc_name": "P15_FS_PLC"}),
        (None, None),
    ],
)
def test_get_plc_by_id_queries_requested_record_and_closes_connection(
    monkeypatch,
    row,
    expected,
):
    connection = _FakeConnection(row)
    monkeypatch.setattr(
        plc_registry_module,
        "get_connection",
        lambda: connection,
    )

    assert PLCRegistryManager.get_plc_by_id(7) == expected
    assert connection.cursor_instance.parameters == (7,)
    assert connection.closed is True
