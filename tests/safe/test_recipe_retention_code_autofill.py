from pathlib import Path


def _template_source() -> str:
    template_path = (
        Path(__file__).resolve().parents[2]
        / "flask_app"
        / "templates"
        / "recipes"
        / "recipe_retention_confirm.html"
    )
    return template_path.read_text(encoding="utf-8")


def test_archive_and_delete_codes_are_prefilled_and_read_only():
    source = _template_source()

    assert '{% if action_kind in ["archive", "delete"] %}' in source
    assert 'value="{{ recipe.recipe_code }}"' in source
    assert "readonly" in source
    assert 'aria-readonly="true"' in source
    assert "Selected automatically from the archived recipe list" in source
    assert "Selected automatically from the recipe list" in source


def test_permanent_delete_uses_single_action_confirmation():
    source = _template_source()

    assert '{% if action_kind == "delete" %}' in source
    assert 'name="delete_confirmation"' not in source
    assert "Type DELETE" not in source
    assert "Enter the deletion reason and press Delete Permanently." in source


def test_other_retention_actions_keep_manual_recipe_code_confirmation():
    source = _template_source()

    assert "Type the exact recipe code to confirm" in source
    assert 'placeholder="{{ recipe.recipe_code }}"' in source
