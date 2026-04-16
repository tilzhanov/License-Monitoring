"""Phase 03.1 UI Polish smoke tests — grep-style file assertions.

These tests pin the design-system foundation: token presence in CSS, font
loading order in base.html, skip-link, icon sprite, focus-visible, and
status row classes. They run in <1s and must stay green through every
subsequent 03.1 plan. See .planning/phases/03.1-ui-polish/03.1-UI-SPEC.md
for locked values.
"""
from pathlib import Path

import pytest

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


# ---------- Plan 03.1-02: Dashboard polish assertions ----------

INDEX = ROOT / "templates" / "index.html"
PARTIAL_TABLE = ROOT / "templates" / "partials" / "license_table.html"


def _index() -> str:
    return INDEX.read_text(encoding="utf-8")


def _partial_table() -> str:
    return PARTIAL_TABLE.read_text(encoding="utf-8")


def test_index_preserves_stats_section_htmx():
    html = _index()
    assert 'id="stats-section"' in html
    assert 'hx-get="/"' in html
    assert 'hx-trigger="license-changed from:body"' in html
    assert 'hx-target="#stats-section"' in html
    assert 'hx-select="#stats-section"' in html
    assert 'hx-swap="outerHTML"' in html


def test_index_preserves_filter_htmx():
    html = _index()
    assert 'hx-get="/licenses/table"' in html
    assert 'hx-target="#license-tbody"' in html
    assert 'hx-trigger="keyup changed delay:300ms"' in html
    assert 'hx-trigger="change"' in html
    assert "hx-include=" in html


def test_index_stat_cards_label_first():
    # Spec §Component 3 requires label BEFORE count (inverted from current).
    html = _index()
    assert 'class="stat-card total"' in html
    assert 'class="stat-card warning"' in html
    assert 'class="stat-card expired"' in html
    for variant in ["total", "warning", "expired"]:
        card_start = html.find(f'class="stat-card {variant}"')
        assert card_start != -1
        slice_ = html[card_start:card_start + 500]
        label_idx = slice_.find('class="label"')
        count_idx = slice_.find('class="count"')
        assert label_idx != -1 and count_idx != -1, f"card {variant} missing label/count"
        assert label_idx < count_idx, f"card {variant} must render label BEFORE count"


def test_index_expiring_widget_has_alert_icon():
    html = _index()
    assert 'class="expiring-widget"' in html
    assert 'href="#icon-alert-triangle"' in html


def test_index_table_container_wrapper():
    html = _index()
    assert 'class="table-container"' in html
    assert 'class="license-table"' in html


def test_index_sortable_th_keyboard_and_chevrons():
    html = _index()
    assert 'role="button"' in html
    assert 'tabindex="0"' in html
    assert 'href="#icon-chevron-up"' in html
    assert 'href="#icon-chevron-down"' in html
    assert "&#9650;" not in html
    assert "&#9660;" not in html


def test_index_filter_search_icon_and_plus_button():
    html = _index()
    assert 'class="filter-search"' in html
    assert 'href="#icon-search"' in html
    assert 'href="#icon-plus"' in html
    assert "Добавить лицензию" in html


def test_index_empty_state_locked_copy():
    html = _index()
    assert "Пока нет лицензий" in html
    assert "Добавьте первую лицензию" in html


def test_partial_table_uses_status_badge_macro():
    html = _partial_table()
    assert "import status_badge" in html
    assert "status_badge(item.status)" in html


def test_partial_table_preserves_delete_htmx():
    html = _partial_table()
    assert 'hx-delete="/licenses/' in html
    assert 'hx-confirm="Удалить лицензию' in html
    assert 'hx-target="closest tr"' in html
    assert 'hx-swap="outerHTML"' in html


def test_partial_table_preserves_status_row_classes():
    html = _partial_table()
    assert "{{ item.status_class }}" in html


def test_index_no_inline_styles():
    html = _index()
    assert "style=" not in html, "inline style attributes must be removed from index.html"


def test_index_imports_macros():
    html = _index()
    assert "from \"partials/_macros.html\" import status_badge" in html or \
           "from 'partials/_macros.html' import status_badge" in html


# ---------- Plan 03.1-03: Form, detail, 404 polish assertions ----------

FORM = ROOT / "templates" / "license_form.html"
DETAIL = ROOT / "templates" / "license_detail.html"
NOT_FOUND = ROOT / "templates" / "404.html"


def _form() -> str:
    return FORM.read_text(encoding="utf-8")


def _detail() -> str:
    return DETAIL.read_text(encoding="utf-8")


def _404() -> str:
    return NOT_FOUND.read_text(encoding="utf-8")


def test_form_container_and_card():
    html = _form()
    assert 'class="form-container"' in html
    assert 'class="form-card"' in html
    # No inline styles
    assert "style=" not in html


def test_form_required_labels():
    html = _form()
    # Product name and expiry date form-groups are marked required so CSS `::after " *"` fires
    # Required groups use `class="form-group required"`
    assert 'class="form-group required"' in html
    # At least two required fields (product_name, expiry_date)
    assert html.count('class="form-group required"') >= 2


def test_form_field_error_icon():
    html = _form()
    # Error blocks must render the alert-triangle icon via sprite
    assert 'href="#icon-alert-triangle"' in html
    assert 'class="field-error"' in html


def test_form_preserves_field_names():
    html = _form()
    for name in ['name="product_name"', 'name="purchase_date"',
                 'name="expiry_date"', 'name="responsible"',
                 'name="cost"', 'name="comment"']:
        assert name in html, f"form missing {name}"


def test_form_actions_verb_noun_copy():
    html = _form()
    # Primary CTA is one of the two verb+noun variants (new or edit context)
    assert ("Сохранить лицензию" in html) or ("Сохранить изменения" in html) or \
           ("{{ submit_text }}" in html)
    # Secondary CTA must be verb+noun — NOT bare "Отмена" or "Вернуться к списку"
    assert "Отменить изменения" in html
    assert "Вернуться к списку" not in html


def test_detail_breadcrumb_and_header():
    html = _detail()
    assert 'class="breadcrumb"' in html
    assert 'href="#icon-arrow-left"' in html
    assert 'class="detail-header"' in html
    # Status badge macro used in detail header
    assert "import status_badge" in html
    assert "status_badge(status)" in html


def test_detail_action_ctas_verb_noun():
    html = _detail()
    assert "Изменить лицензию" in html
    assert "Вернуться к дашборду" in html
    # Single-word "Изменить" as a standalone CTA must be gone
    assert ">Изменить<" not in html
    assert "Назад к дашборду" not in html


def test_detail_no_inline_styles():
    html = _detail()
    assert "style=" not in html


def test_detail_preserves_jinja_vars():
    html = _detail()
    # Context var names pinned by router + test_licenses.py:207
    assert "license.product_name" in html
    assert "license.expiry_date" in html
    assert "license.purchase_date" in html
    assert "license.responsible" in html
    assert "license.cost" in html
    assert "license.comment" in html
    assert "days_left" in html


def test_404_dynamic_title():
    html = _404()
    # Dynamic title keeps test_licenses.py:215 green AND lets generic 404s show spec copy
    assert "title if title" in html
    assert "Страница не найдена" in html
    assert "Запрошенный ресурс не существует или был удалён." in html
    assert 'href="#icon-x-circle"' in html
    # Back link uses btn-secondary class and locked copy
    assert "Вернуться на дашборд" in html
    assert "btn-secondary" in html


def test_404_no_inline_styles():
    assert "style=" not in _404()


# ---------- Plan 03.1-04: HTMX polish, a11y, requirement coverage assertions ----------

REQS = ROOT / ".planning" / "REQUIREMENTS.md"


def test_ui16_htmx_request_indicators():
    css = _css()
    assert "#license-tbody.htmx-request" in css
    assert "opacity: 0.6" in css
    assert "pointer-events: none" in css
    assert "#stats-section.htmx-request" in css
    assert "@keyframes fadeIn" in css
    assert "animation: fadeIn" in css


def test_ui17_skip_link_styled():
    css = _css()
    assert ".skip-link" in css
    # Hidden state (off-screen top) + visible on focus
    assert "top: -40px" in css or "top:-40px" in css
    assert ".skip-link:focus" in css


def test_ui17_universal_focus_visible():
    css = _css()
    # Global rule + button-specific reinforcement
    assert ":focus-visible {" in css or ":focus-visible{" in css
    assert "outline: 2px solid var(--accent-600)" in css
    assert "box-shadow: var(--shadow-focus)" in css


def test_ui17_reduced_motion_disables_transitions():
    css = _css()
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "transition-duration: 0.01ms" in css
    assert "animation-duration: 0.01ms" in css


@pytest.mark.skipif(not REQS.exists(), reason=".planning/ not available in Docker image")  # noqa: E501
def test_ui18_requirement_coverage():
    """Every UI-01..UI-18 ID must be registered in REQUIREMENTS.md."""
    content = REQS.read_text(encoding="utf-8")
    for n in range(1, 19):
        tag = f"UI-{n:02d}"
        assert tag in content, f"{tag} missing from REQUIREMENTS.md"
    # Also present in Traceability table
    assert "UI-18" in content


def test_ui18_all_templates_free_of_inline_styles():
    """RESEARCH Pitfall 6 -- zero inline styles across templates/."""
    for path in ROOT.joinpath("templates").rglob("*.html"):
        body = path.read_text(encoding="utf-8")
        assert "style=" not in body, f"inline style found in {path.relative_to(ROOT)}"


def test_ui18_htmx_attr_preservation():
    """Confirm every HTMX attr from RESEARCH Test Contract Inventory is still present."""
    idx = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    partial = (ROOT / "templates" / "partials" / "license_table.html").read_text(encoding="utf-8")
    for attr in [
        'hx-get="/"',
        'hx-trigger="license-changed from:body"',
        'hx-target="#stats-section"',
        'hx-select="#stats-section"',
        'hx-swap="outerHTML"',
        'hx-get="/licenses/table"',
        'hx-target="#license-tbody"',
        'hx-trigger="keyup changed delay:300ms"',
        'hx-trigger="change"',
    ]:
        assert attr in idx, f"index.html missing {attr}"
    for attr in [
        'hx-delete="/licenses/',
        'hx-confirm="Удалить лицензию',
        'hx-target="closest tr"',
        'hx-swap="outerHTML"',
    ]:
        assert attr in partial, f"license_table.html missing {attr}"
