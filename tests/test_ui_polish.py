"""Phase 03.1 UI Polish smoke tests — grep-style file assertions.

These tests pin the design-system foundation: token presence in CSS, font
loading order in base.html, skip-link, icon sprite, focus-visible, and
status row classes. They run in <1s and must stay green through every
subsequent 03.1 plan. See .planning/phases/03.1-ui-polish/03.1-UI-SPEC.md
for locked values.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSS = ROOT / "static" / "css" / "app.css"
BASE = ROOT / "templates" / "base.html"
ICONS = ROOT / "templates" / "partials" / "icons.html"
MACROS = ROOT / "templates" / "partials" / "_macros.html"


def _css() -> str:
    return CSS.read_text(encoding="utf-8")


def _base() -> str:
    return BASE.read_text(encoding="utf-8")


def test_design_tokens_present():
    css = _css()
    # Spacing scale (12px MUST be absent from scale, only 4/8/16/24/32/48/64)
    for token in ["--space-1:", "--space-2:", "--space-4:", "--space-5:",
                  "--space-6:", "--space-8:", "--space-10:"]:
        assert token in css, f"missing spacing token {token}"
    # Typography
    for token in ["--font-sans:", "--font-mono:", "--text-xs:", "--text-sm:",
                  "--text-lg:", "--text-xl:", "--fw-regular:", "--fw-semibold:"]:
        assert token in css, f"missing typography token {token}"
    # Slate ramp
    for token in ["--slate-50:", "--slate-100:", "--slate-200:", "--slate-300:",
                  "--slate-500:", "--slate-700:", "--slate-900:", "--surface:"]:
        assert token in css, f"missing slate token {token}"
    # Accent
    assert "--accent-600:" in css
    assert "--accent-700:" in css
    # Status tokens
    for token in ["--status-active-bg:", "--status-active-bar:",
                  "--status-warning-bg:", "--status-warning-bar:",
                  "--status-expired-bg:", "--status-expired-bar:",
                  "--destructive:"]:
        assert token in css, f"missing status token {token}"
    # Radius + shadow
    for token in ["--radius-sm:", "--radius-md:", "--radius-lg:",
                  "--shadow-sm:", "--shadow-focus:"]:
        assert token in css, f"missing radius/shadow token {token}"
    # Locked HEX values from UI-SPEC §Color
    for hex_value in ["#0F172A", "#2563EB", "#F8FAFC", "#22C55E",
                      "#F59E0B", "#EF4444", "#DC2626"]:
        assert hex_value in css, f"missing locked hex {hex_value}"


def test_font_links_in_base():
    html = _base()
    assert 'rel="preconnect" href="https://fonts.googleapis.com"' in html
    assert 'rel="preconnect" href="https://fonts.gstatic.com"' in html
    assert "fonts.googleapis.com/css2?family=Inter" in html
    assert "JetBrains+Mono" in html
    assert "display=swap" in html
    # Fonts MUST load before app.css
    fonts_idx = html.find("fonts.googleapis.com/css2")
    css_idx = html.find("css/app.css")
    assert fonts_idx != -1 and css_idx != -1
    assert fonts_idx < css_idx, "fonts must be linked BEFORE app.css"


def test_skip_link_and_main_id_in_base():
    html = _base()
    assert 'class="skip-link"' in html
    assert 'href="#main"' in html
    assert 'id="main"' in html
    assert "Перейти к содержимому" in html


def test_brand_text_preserved():
    # test_health.py:69 pins this literally
    assert "License Monitor" in _base()


def test_icon_sprite_included_and_complete():
    html = _base()
    assert 'partials/icons.html' in html
    assert ICONS.exists(), "templates/partials/icons.html must exist"
    sprite = ICONS.read_text(encoding="utf-8")
    for icon_id in [
        "icon-layout-dashboard", "icon-plus", "icon-pencil", "icon-trash-2",
        "icon-chevron-up", "icon-chevron-down", "icon-search",
        "icon-alert-triangle", "icon-check-circle-2", "icon-x-circle",
        "icon-calendar", "icon-arrow-left",
    ]:
        assert f'id="{icon_id}"' in sprite, f"sprite missing {icon_id}"


def test_status_row_classes_in_css():
    css = _css()
    for selector in ["tr.status-active", "tr.status-warning", "tr.status-expired"]:
        assert selector in css, f"missing row selector {selector}"
    assert "inset 4px 0 0 0" in css, "status rows must use inset left bar box-shadow"


def test_focus_visible_and_reduced_motion_in_css():
    css = _css()
    assert ":focus-visible" in css
    assert "prefers-reduced-motion" in css
    assert "--shadow-focus" in css


def test_status_badge_macro_exists():
    assert MACROS.exists(), "templates/partials/_macros.html must exist"
    macros = MACROS.read_text(encoding="utf-8")
    assert "macro status_badge" in macros
    assert "status-badge-active" in macros
    assert "status-badge-warning" in macros
    assert "status-badge-expired" in macros
    assert "Активна" in macros
    assert "Скоро истекает" in macros
    assert "Истекла" in macros


def test_nav_has_dashboard_icon_and_main_wrapper():
    html = _base()
    # Nav brand must reference layout-dashboard icon via sprite <use>
    assert 'href="#icon-layout-dashboard"' in html
    # main wrapper with id for skip-link target
    assert '<main id="main">' in html
