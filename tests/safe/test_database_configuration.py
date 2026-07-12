from database.database_configuration_manager import DatabaseConfigurationManager


def _valid_fields():
    return {
        "host": "mysql.crs.local",
        "port": "3306",
        "database": "crs_production",
        "username": "crs_app",
        "password": "not-a-real-password",
        "ssl_mode": "required",
        "ssl_ca_path": "",
    }


def test_database_configuration_rejects_unsafe_database_name():
    fields = _valid_fields()
    fields["database"] = "crs`; DROP DATABASE mysql; --"

    _, errors = DatabaseConfigurationManager.validate_fields(fields)

    assert any("letters, numbers, and underscores" in error for error in errors)


def test_database_url_masks_password():
    fields, errors = DatabaseConfigurationManager.validate_fields(_valid_fields())

    assert errors == []
    masked = DatabaseConfigurationManager._connection_url(fields).render_as_string(
        hide_password=True
    )
    assert "not-a-real-password" not in masked
    assert "***" in masked


def test_saved_profile_uses_secret_protection(monkeypatch, tmp_path):
    profile_path = tmp_path / "instance" / "database_profile.json"
    monkeypatch.setattr(DatabaseConfigurationManager, "PROFILE_PATH", profile_path)
    monkeypatch.setattr(
        DatabaseConfigurationManager,
        "_protect_secret",
        classmethod(lambda cls, value: "protected-test-value"),
    )

    saved = DatabaseConfigurationManager.save_profile(
        _valid_fields(),
        updated_by="admin",
    )
    content = profile_path.read_text(encoding="utf-8")

    assert saved["password_saved"] is True
    assert "not-a-real-password" not in content
    assert "protected-test-value" in content
    assert saved["runtime_activation"] == "blocked_pending_sqlalchemy_migration"

