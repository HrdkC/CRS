from pathlib import Path


def test_archive_confirmation_code_is_prefilled_and_read_only():
    template_path = (
        Path(__file__).resolve().parents[2]
        / "flask_app"
        / "templates"
        / "recipes"
        / "recipe_retention_confirm.html"
    )
    source = template_path.read_text(encoding="utf-8")

    assert '{% if action_kind in ["archive", "delete"] %}' in source
    assert 'value="{{ recipe.recipe_code }}"' in source
    assert "readonly" in source
    assert "Selected automatically from the recipe list." in source


def test_restore_keeps_manual_recipe_code_confirmation():
    template_path = (
        Path(__file__).resolve().parents[2]
        / "flask_app"
        / "templates"
        / "recipes"
        / "recipe_retention_confirm.html"
    )
    source = template_path.read_text(encoding="utf-8")

    assert "Type the exact recipe code to confirm" in source
    assert '{% if action_kind == "delete" %}' in source
    assert 'name="delete_confirmation"' not in source
