---
phase: 02-dashboard
verified: 2026-04-06T10:30:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
gaps: []
human_verification:
  - test: "Visual check of color-coded rows in browser"
    expected: "Expired rows display with red background, warning rows with yellow, active rows with green — all visible without clicking anything"
    why_human: "CSS rendering and color appearance cannot be verified programmatically"
  - test: "HTMX filter debounce behavior"
    expected: "Typing in the product search box triggers a filtered table update after 300ms delay without full page reload"
    why_human: "JavaScript execution and DOM swapping requires a browser"
---

# Phase 2: Dashboard Verification Report

**Phase Goal:** Users can see the full state of all licenses at a glance without needing to open any records
**Verified:** 2026-04-06T10:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Main page shows three summary counters: total, expiring soon, already expired | VERIFIED | `templates/index.html` lines 9-22: `stats-grid` div with `stat-card total`, `stat-card warning`, `stat-card expired`; `pages.py` computes `total`, `expiring`, `expired_count`; `test_stats_counters` passes |
| 2 | "Expiring Soon" widget lists licenses approaching threshold with product name, expiry date, and days remaining | VERIFIED | `templates/index.html` lines 25-42: `expiring-widget` section renders `item.license.product_name`, `item.license.expiry_date`, `item.days_remaining`; `pages.py` line 30-33 produces `expiring_soon` sorted top-10; `test_expiring_soon_widget` passes |
| 3 | License table rows are color-coded: red/yellow/green applied server-side, visible without interaction | VERIFIED | `partials/license_table.html` line 2: `<tr class="{{ item.status_class }}">` — server-side class injection; CSS `.status-expired`, `.status-warning`, `.status-active` in `app.css` lines 96-101; `test_status_color_classes` passes |
| 4 | Status is computed server-side from today's date and expiry date — no manual status field | VERIFIED | `app/services/status.py`: `get_license_status()` derives status from `days_until_expiry()` vs threshold; `enrich_licenses()` adds `status_class` to each dict; no manual `status` column in `License` model; 14 unit tests pass in `test_status.py` |
| 5 | Table can be filtered by product/status and sorted by expiry date/product name without full page reload | VERIFIED | `pages.py` line 53-93: `GET /licenses/table` endpoint with `product`, `status`, `sort`, `order` query params; `index.html` lines 49-66: HTMX attributes `hx-get`, `hx-trigger`, `hx-target`, `hx-include` wired; 9 filter/sort integration tests pass |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/services/__init__.py` | Package init | VERIFIED | Exists, empty (correct for package init) |
| `app/services/status.py` | Status computation functions | VERIFIED | 64 lines; exports `days_until_expiry`, `get_license_status`, `get_global_threshold`, `enrich_licenses`; real logic, no stubs |
| `tests/test_status.py` | Unit tests for status computation | VERIFIED | 113 lines (> 40 min); 14 test functions; all pass |
| `app/routers/pages.py` | Dashboard route GET / with stats, widget, table; HTMX partial GET /licenses/table | VERIFIED | 94 lines; `def index(...)` and `def license_table(...)` both present with full logic |
| `templates/index.html` | Full dashboard template with stats, expiring widget, table | VERIFIED | 96 lines (> 50 min); `stats-grid`, `expiring-widget`, `license-table`, HTMX attributes all present |
| `templates/partials/license_table.html` | Reusable tbody fragment | VERIFIED | 13 lines (> 10 min); renders `item.status_class`, `item.license.product_name`, `item.days_remaining` |
| `static/css/app.css` | Status color classes and card layout | VERIFIED | Contains `.status-expired`, `.status-warning`, `.status-active`, `.stats-grid`, `.stat-card`, `.license-table`, `.expiring-widget`, `.filter-controls`, `@media (max-width: 768px)` |
| `tests/test_dashboard.py` | Integration tests for dashboard routes | VERIFIED | 235 lines (> 60 min); 14 test functions including `test_stats_counters`, `test_expiring_soon_widget`, `test_status_color_classes`, `test_filter_by_product`, `test_filter_by_status`, `test_sort_by_product_name`; all pass |
| `tests/conftest.py` | `make_license` factory and `seed_default_settings` fixtures | VERIFIED | Both fixtures present at lines 36-56; used by `test_status.py` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `app/services/status.py` | `app/models.py` | `from app.models import AppSettings, License` | WIRED | Line 8: `from app.models import AppSettings, License` |
| `app/services/status.py` | `app/config.py` | `from app.config import NOTIFY_DAYS_BEFORE` | WIRED | Line 7: `from app.config import NOTIFY_DAYS_BEFORE` |
| `app/routers/pages.py` | `app/services/status.py` | `from app.services.status import get_global_threshold, enrich_licenses` | WIRED | Line 8: `from app.services.status import enrich_licenses, get_global_threshold` |
| `app/routers/pages.py` | `app/models.py` | `db.query(License)` | WIRED | Lines 22, 64: `db.query(License).all()` — real DB queries |
| `templates/index.html` | `templates/partials/license_table.html` | Jinja2 include for tbody | WIRED | Line 90: `{% include "partials/license_table.html" %}` |
| `templates/index.html` | `app/routers/pages.py` | `hx-get="/licenses/table"` | WIRED | Lines 50, 55: `hx-get="/licenses/table"` on both filter controls |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `templates/index.html` | `total`, `expiring`, `expired`, `expiring_soon`, `licenses` | `pages.py index()` → `db.query(License).all()` + `enrich_licenses()` | Yes — real SQLAlchemy DB query; `enrich_licenses` computes from live data | FLOWING |
| `templates/partials/license_table.html` | `licenses` (list of enriched dicts) | `pages.py license_table()` → `db.query(License)` with filters + `enrich_licenses()` | Yes — DB query with ilike filter; status filtering on enriched list | FLOWING |
| `app/services/status.py enrich_licenses()` | `lic.expiry_date`, `lic.notify_days_before` | `License` ORM objects from DB session | Yes — reads real fields from persisted License rows | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `GET /` returns 200 with stats and empty state | `pytest tests/test_dashboard.py::test_dashboard_empty_db -v` | PASSED | PASS |
| Stats counters show correct counts | `pytest tests/test_dashboard.py::test_stats_counters -v` | PASSED | PASS |
| Expiring soon widget populated | `pytest tests/test_dashboard.py::test_expiring_soon_widget -v` | PASSED | PASS |
| Color classes present in HTML | `pytest tests/test_dashboard.py::test_status_color_classes -v` | PASSED | PASS |
| HTMX partial endpoint returns rows | `pytest tests/test_dashboard.py::test_table_partial_endpoint -v` | PASSED | PASS |
| Filter by product works | `pytest tests/test_dashboard.py::test_filter_by_product -v` | PASSED | PASS |
| Filter by status works | `pytest tests/test_dashboard.py::test_filter_by_status -v` | PASSED | PASS |
| Sort ascending/descending works | `pytest tests/test_dashboard.py::test_sort_by_expiry_desc -v` | PASSED | PASS |
| HTMX attributes present on index | `pytest tests/test_dashboard.py::test_htmx_attributes_on_index -v` | PASSED | PASS |
| Full test suite (49 tests) | `python3 -m pytest tests/ -v` | 49 passed in 0.47s | PASS |

Note: Direct `TestClient` spot-check outside pytest fails because `DB_PATH=/data/licenses.db` (Docker volume path) is not accessible on the host. The pytest suite correctly overrides the DB session; that is the authoritative behavioral verification.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| LIC-05 | 02-01-PLAN.md | Статус вычисляется автоматически: активна / скоро истекает / истекла | SATISFIED | `app/services/status.py` computes status from `expiry_date` and threshold; no manual status field; 14 unit tests verify all boundary conditions |
| DASH-01 | 02-02-PLAN.md | Главная страница отображает общую статистику: всего лицензий, истекает в ближайшее время, уже истекло | SATISFIED | `index.html` stats-grid cards; `pages.py` computes `total`, `expiring`, `expired_count`; `test_stats_counters` passes |
| DASH-02 | 02-02-PLAN.md | На главной странице есть виджет «Скоро истекающие» | SATISFIED | `expiring-widget` section in `index.html`; top-10 warning licenses sorted by days remaining; `test_expiring_soon_widget` passes |
| DASH-03 | 02-02-PLAN.md | Таблица всех лицензий с цветовой подсветкой строк по статусу | SATISFIED | `partials/license_table.html` applies `status_class` to `<tr>`; CSS provides red/yellow/green colors; `test_status_color_classes` passes |
| DASH-04 | 02-03-PLAN.md | Таблица поддерживает фильтрацию и сортировку | SATISFIED | `GET /licenses/table` endpoint with product/status filter and sort params; HTMX wired in `index.html`; 9 filter/sort tests pass |

**Orphaned requirements check:** REQUIREMENTS.md traceability table maps DASH-01, DASH-02, DASH-03, DASH-04 to Phase 2 with status "Complete". LIC-05 is mapped to Phase 2 with status "Pending" — however the plan (02-01) explicitly claims LIC-05 and implements it. The checkbox in REQUIREMENTS.md is still unchecked (`[ ] LIC-05`) while DASH-01 through DASH-04 are checked. This is a documentation discrepancy only; the implementation is verified above. No orphaned requirements.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `templates/index.html` | 54 | `placeholder="Поиск по продукту..."` | Info | HTML input placeholder attribute — not a code stub; intended UX copy |

No blockers or warnings found. The single grep match is a legitimate HTML input `placeholder` attribute for the search box, not a placeholder implementation.

### Human Verification Required

#### 1. Color-coded row appearance

**Test:** Load the dashboard in a browser with at least one expired, one warning, and one active license in the database. Inspect the table rows visually.
**Expected:** Expired rows have a red background (`#fce4e4`), warning rows have a yellow background (`#fff8e1`), active rows have a green background (`#e8f5e9`) — all visible without clicking or hovering.
**Why human:** CSS rendering and color perception cannot be verified programmatically.

#### 2. HTMX filter live behavior

**Test:** Open the dashboard in a browser. Type characters into the product search box and observe the table.
**Expected:** The table rows update to show only matching products after a 300ms debounce, without a full page reload. No flash or scroll jump occurs.
**Why human:** JavaScript execution, DOM partial swapping, and debounce timing require a browser with HTMX running.

### Gaps Summary

No gaps. All five observable truths are verified, all artifacts pass all four levels (exists, substantive, wired, data flowing), all key links are confirmed, and the full 49-test suite passes with zero failures.

---

_Verified: 2026-04-06T10:30:00Z_
_Verifier: Claude (gsd-verifier)_
