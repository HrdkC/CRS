from pathlib import Path


def test_delete_confirmation_field_is_not_rendered():
    template = Path(
        "flask_app/templates/recipes/recipe_retention_confirm.html"
    ).read_text(encoding="utf-8")

    assert 'name="delete_confirmation"' not in template
    assert 'id="delete_confirmation"' not in template
    assert "Type DELETE" not in template
    assert "Enter the deletion reason and press Delete Permanently." in template


def test_delete_route_does_not_read_delete_confirmation():
    route_source = Path("flask_app/routes/recipe_routes.py").read_text(
        encoding="utf-8"
    )

    assert 'request.form.get("delete_confirmation")' not in route_source


def test_manager_keeps_compatibility_without_requiring_delete_phrase():
    manager_source = Path("database/recipe_retention_manager.py").read_text(
        encoding="utf-8"
    )

    assert "delete_confirmation=None" in manager_source
    assert "Type DELETE to confirm permanent deletion." not in manager_source
