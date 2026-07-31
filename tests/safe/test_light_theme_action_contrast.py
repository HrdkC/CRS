from pathlib import Path
import re

from scripts.build_css_bundle import OUTPUT_PATH, render_bundle


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CSS_ROOT = PROJECT_ROOT / "flask_app" / "static" / "css"
MAIN_CSS = CSS_ROOT / "main.css"
MODULE = CSS_ROOT / "modules" / "39_light_theme_action_contrast.css"
BASE_TEMPLATE = PROJECT_ROOT / "flask_app" / "templates" / "base.html"
TEMPLATE_ROOT = PROJECT_ROOT / "flask_app" / "templates"


def _rgb(hex_color):
    value = hex_color.lstrip("#")
    return tuple(int(value[index : index + 2], 16) / 255 for index in (0, 2, 4))


def _relative_luminance(hex_color):
    channels = []
    for channel in _rgb(hex_color):
        channels.append(
            channel / 12.92
            if channel <= 0.04045
            else ((channel + 0.055) / 1.055) ** 2.4
        )
    red, green, blue = channels
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _contrast_ratio(first, second):
    lighter, darker = sorted(
        (_relative_luminance(first), _relative_luminance(second)),
        reverse=True,
    )
    return (lighter + 0.05) / (darker + 0.05)


def test_light_theme_contrast_module_is_last_and_bundle_is_current():
    manifest = MAIN_CSS.read_text(encoding="utf-8")
    base_template = BASE_TEMPLATE.read_text(encoding="utf-8")

    import_line = (
        '@import url("./modules/39_light_theme_action_contrast.css?'
        'v=css-v135-light-action-contrast-20260731");'
    )
    assert manifest.rstrip().endswith(import_line)
    assert "css-v135-light-action-contrast-20260731" in base_template
    assert OUTPUT_PATH.read_text(encoding="utf-8") == render_bundle()


def test_active_light_theme_action_text_meets_wcag_aa_contrast():
    pairs = {
        "primary": ("#ffffff", "#1d4ed8"),
        "primary-hover": ("#ffffff", "#1e40af"),
        "violet": ("#ffffff", "#6d28d9"),
        "violet-hover": ("#ffffff", "#5b21b6"),
        "neutral": ("#ffffff", "#334155"),
        "neutral-hover": ("#ffffff", "#1e293b"),
        "soft": ("#1e293b", "#e2e8f0"),
        "soft-hover": ("#0f172a", "#cbd5e1"),
        "success": ("#ffffff", "#15803d"),
        "success-hover": ("#ffffff", "#166534"),
        "warning": ("#ffffff", "#92400e"),
        "warning-hover": ("#ffffff", "#78350f"),
        "danger": ("#ffffff", "#dc2626"),
        "danger-hover": ("#ffffff", "#b91c1c"),
        "unavailable": ("#ffffff", "#475569"),
    }

    failures = {
        name: round(_contrast_ratio(foreground, background), 2)
        for name, (foreground, background) in pairs.items()
        if _contrast_ratio(foreground, background) < 4.5
    }
    assert not failures


def test_light_theme_contract_covers_project_action_families():
    source = MODULE.read_text(encoding="utf-8")
    required_markers = (
        ".crs-btn-primary",
        ".crs-btn-soft",
        ".primary-action",
        ".secondary-action",
        ".row-action",
        ".plc-registry-actions",
        ".buffer",
        ".success",
        ".warning",
        ".danger",
        ".bulk-chip-button",
        ".bulk-action-button",
        ".bulk-sort-button",
        ".row-btn",
        ".operation-button",
        ":disabled",
        '[aria-disabled="true"]',
        "-webkit-text-fill-color",
        ":focus-visible",
    )

    for marker in required_markers:
        assert marker in source


def test_plc_registry_test_verify_and_array_import_have_explicit_contrast():
    source = MODULE.read_text(encoding="utf-8")
    plc_template = (
        TEMPLATE_ROOT / "plcs" / "plcs.html"
    ).read_text(encoding="utf-8")

    assert ".plc-registry-actions :is(a, button).row-action:not(" in source
    assert "var(--crs-light-action-neutral-bg)" in source
    assert "var(--crs-light-action-violet-bg)" in source
    assert 'class="row-action"' in plc_template
    assert 'class="row-action buffer plc-action-array-import"' in plc_template


def test_templates_do_not_add_inline_white_text_to_pale_action_backgrounds():
    suspicious = []
    white_pattern = re.compile(r"color\s*:\s*(?:#fff(?:fff)?|white)", re.I)
    pale_pattern = re.compile(
        r"background(?:-color)?\s*:\s*"
        r"(?:#f[0-9a-f]{5}|#e[0-9a-f]{5}|white|#fff(?:fff)?)",
        re.I,
    )

    for template in TEMPLATE_ROOT.rglob("*.html"):
        text = template.read_text(encoding="utf-8")
        for style in re.findall(r"style\s*=\s*[\"']([^\"']+)[\"']", text, re.I):
            if white_pattern.search(style) and pale_pattern.search(style):
                suspicious.append(f"{template.relative_to(PROJECT_ROOT)}: {style}")

    assert not suspicious
