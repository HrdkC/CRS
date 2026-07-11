import pytest

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
