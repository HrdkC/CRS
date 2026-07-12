from scripts.configure_secret_key import ensure_secret, valid_secret


def test_machine_local_secret_is_created_once(monkeypatch, tmp_path):
    secret_path = tmp_path / "instance" / "crs_secret_key"
    monkeypatch.setenv("CRS_SECRET_KEY_FILE", str(secret_path))

    created_path, created = ensure_secret()
    first_value = created_path.read_text(encoding="utf-8").strip()

    same_path, created_again = ensure_secret()
    second_value = same_path.read_text(encoding="utf-8").strip()

    assert created is True
    assert created_again is False
    assert created_path == secret_path
    assert valid_secret(first_value)
    assert first_value == second_value
