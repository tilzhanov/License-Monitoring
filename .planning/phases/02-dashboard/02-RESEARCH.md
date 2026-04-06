# Phase 2: Dashboard - Research

**Researched:** 2026-04-06
**Domain:** FastAPI + Jinja2 + HTMX server-rendered dashboard with filtering/sorting
**Confidence:** HIGH

## Summary

Phase 2 builds a read-only dashboard as the main landing page, replacing the current placeholder at `/`. The dashboard shows summary stats (total, expiring soon, expired), an expiring-soon widget, and a full license table with color-coded rows. The table supports HTMX-driven filtering (by product name and status) and sorting (by expiry date and product name) without full page reloads.

All technology is already in the project: FastAPI 0.135.3, Jinja2 3.1.6, SQLAlchemy 2.0.49, HTMX 2.0.4 (CDN in base.html). No new dependencies are needed. The work is purely backend route logic, a status computation service, Jinja2 templates, and CSS.

**Primary recommendation:** Build a `status.py` service module for status computation, extend the existing `pages.py` router with dashboard logic and an HTMX partial endpoint, create Jinja2 templates with fragment includes, and add status color CSS classes.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Status computed server-side from `expiry_date` and threshold. Three states: `active` (days > threshold), `warning` (0 < days <= threshold), `expired` (days <= 0).
- **D-02:** Threshold = per-license `notify_days_before` if set, else global default (60 days from `app_settings`).
- **D-03:** `days_until_expiry()` helper function in a new `app/services/status.py` module.
- **D-04:** Single-column layout: stats counters at top, expiring-soon widget below, full license table at bottom.
- **D-05:** Stats counters: 3 cards -- Total, Expiring Soon, Expired -- each showing count.
- **D-06:** Expiring-soon widget: top 5-10 licenses sorted by days remaining ascending, showing product name, expiry date, days remaining.
- **D-07:** Table row CSS classes: `status-expired` (red), `status-warning` (yellow/amber), `status-active` (green). Applied server-side via Jinja2.
- **D-08:** HTMX-powered -- filter/sort controls send GET requests, server returns HTML table fragment replacing `<tbody>`.
- **D-09:** Filter by: product name (text input), status (dropdown: all/active/warning/expired).
- **D-10:** Sort by: expiry date (asc/desc), product name (asc/desc). Default: expiry date ascending.
- **D-11:** `GET /` -- full dashboard page (stats + widget + table).
- **D-12:** `GET /licenses/table` -- HTMX partial returning only `<tbody>` for filter/sort updates.

### Claude's Discretion
- Exact CSS colors and card styling (within the constraint of red/yellow/green for statuses)
- Empty state message when no licenses exist
- Exact number of licenses in expiring-soon widget
- Table column ordering
- Navigation bar additions

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DASH-01 | Stats counters: total / expiring soon / expired | Status service computes counts; route passes to template context; 3-card layout |
| DASH-02 | Expiring-soon widget on main page | Query licenses WHERE status=warning, ORDER BY days_remaining ASC LIMIT N |
| DASH-03 | Color-coded table rows (red/yellow/green) | CSS classes `status-expired`, `status-warning`, `status-active` set in Jinja2 template |
| DASH-04 | Filter by product/status, sort by date/name via HTMX | HTMX partial endpoint `GET /licenses/table` with query params, `hx-get` + `hx-target` on controls |
| LIC-05 | Status computed automatically from dates | `days_until_expiry()` in `app/services/status.py`, threshold from per-license or global setting |

</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Sync routes only:** All DB-touching routes use `sync def`, not `async def`
- **HTMX responses:** Return HTML fragments via Jinja2, not JSON
- **Templates singleton:** Use `app/templates.py` -- do NOT instantiate Jinja2Templates in routers
- **Settings precedence:** DB value -> .env -> hardcoded default
- **Status thresholds:** expired = days <= 0, warning = days <= threshold, active = days > threshold
- **Tests:** pytest, integration-style with real DB, in `tests/`
- **No JS build step:** All interactivity via HTMX attributes
- **UI language:** Russian (team is Russian-speaking)

## Standard Stack

### Core (already installed -- no new packages needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.135.3 | Web framework, routing | Already in project |
| SQLAlchemy | 2.0.49 | ORM, database queries | Already in project |
| Jinja2 | 3.1.6 | Server-side HTML templates | Already in project |
| HTMX | 2.0.4 (CDN) | Client-side partial page updates | Already in base.html |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.0.2 | Test framework | Integration tests for routes and status logic |

### Alternatives Considered

None needed. The stack is fully decided and installed. No new dependencies required for this phase.

**Installation:** No additional packages needed. All dependencies are in `requirements.txt`.

## Architecture Patterns

### New Files Structure

```
app/
├── services/
│   └── status.py        # days_until_expiry(), get_license_status(), get_threshold()
├── routers/
│   └── pages.py         # Extend: dashboard route (GET /) + table partial (GET /licenses/table)
templates/
├── index.html           # Rewrite: full dashboard (extends base.html)
├── partials/
│   └── license_table.html  # HTMX fragment: <tbody> rows only
static/
├── css/
│   └── app.css          # Extend: status colors, card layout, table styles
tests/
├── test_status.py       # Unit tests for status computation
├── test_dashboard.py    # Integration tests for dashboard routes
```

### Pattern 1: Status Computation Service

**What:** Pure function that computes license status from dates and threshold.
**When to use:** Every time licenses are displayed (dashboard, table, widget).
**Example:**

```python
# app/services/status.py
from datetime import date
from sqlalchemy.orm import Session
from app.models import AppSettings


def get_global_threshold(db: Session) -> int:
    """Get global notification threshold from DB, fallback to env, fallback to 60."""
    setting = db.query(AppSettings).filter_by(key="notify_days_before").first()
    if setting and setting.value:
        return int(setting.value)
    from app.config import NOTIFY_DAYS_BEFORE
    return NOTIFY_DAYS_BEFORE


def days_until_expiry(expiry_date: date) -> int:
    """Days from today until expiry. Negative = already expired."""
    return (expiry_date - date.today()).days


def get_license_status(expiry_date: date, threshold: int) -> str:
    """Return 'expired', 'warning', or 'active'."""
    days = days_until_expiry(expiry_date)
    if days <= 0:
        return "expired"
    elif days <= threshold:
        return "warning"
    return "active"
```

### Pattern 2: HTMX Partial Response

**What:** Single route that returns a full page or just a `<tbody>` fragment depending on whether the request comes from HTMX.
**When to use:** For filter/sort updates that should not cause a full page reload.
**Example:**

```python
# In app/routers/pages.py
from fastapi import APIRouter, Request, Query
from typing import Optional
from app.database import SessionDep
from app.templates import templates

router = APIRouter()

@router.get("/licenses/table")
def license_table(
    request: Request,
    db: SessionDep,
    product: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    sort: str = Query("expiry_date"),
    order: str = Query("asc"),
):
    # Build query with filters, compute status for each row
    # Return only the tbody partial
    return templates.TemplateResponse(
        request=request,
        name="partials/license_table.html",
        context={"licenses": enriched_licenses},
    )
```

### Pattern 3: HTMX Filter/Sort Controls

**What:** HTML form controls with `hx-get` that trigger table updates.
**When to use:** For the filter inputs and sort headers above the table.
**Example:**

```html
<!-- Filter controls -->
<input type="text" name="product"
       hx-get="/licenses/table"
       hx-trigger="keyup changed delay:300ms"
       hx-target="#license-tbody"
       hx-include="[name='status'],[name='sort'],[name='order']"
       placeholder="Поиск по продукту...">

<select name="status"
        hx-get="/licenses/table"
        hx-trigger="change"
        hx-target="#license-tbody"
        hx-include="[name='product'],[name='sort'],[name='order']">
    <option value="">Все</option>
    <option value="active">Активные</option>
    <option value="warning">Скоро истекает</option>
    <option value="expired">Истекшие</option>
</select>

<!-- Table with replaceable tbody -->
<table>
  <thead>
    <tr>
      <th hx-get="/licenses/table?sort=product_name&order=asc"
          hx-target="#license-tbody"
          hx-include="[name='product'],[name='status']"
          style="cursor:pointer">Продукт</th>
      <!-- ... more headers ... -->
    </tr>
  </thead>
  <tbody id="license-tbody">
    {% include "partials/license_table.html" %}
  </tbody>
</table>
```

### Pattern 4: Enriched License Data for Templates

**What:** Before passing licenses to templates, enrich each with computed status and days remaining.
**When to use:** In the dashboard route and table partial route.
**Example:**

```python
def enrich_licenses(licenses, global_threshold):
    """Add computed status and days_remaining to each license for templates."""
    result = []
    for lic in licenses:
        threshold = lic.notify_days_before or global_threshold
        days = days_until_expiry(lic.expiry_date)
        status = get_license_status(lic.expiry_date, threshold)
        result.append({
            "license": lic,
            "days_remaining": days,
            "status": status,
            "status_class": f"status-{status}",
        })
    return result
```

### Anti-Patterns to Avoid
- **Storing status in DB:** Status MUST be computed, not stored. It changes daily.
- **Async def for DB routes:** Project convention is sync def for all DB-touching endpoints.
- **Returning JSON from HTMX endpoints:** HTMX expects HTML fragments, not JSON.
- **Instantiating Jinja2Templates in routers:** Use the singleton from `app/templates.py`.
- **Client-side status logic:** All status computation is server-side; HTMX just swaps HTML.
- **Using `hx-swap="innerHTML"` on tbody:** The default `hx-swap="innerHTML"` works for `hx-target="#license-tbody"`, but ensure the partial returns `<tr>` rows directly (no wrapping `<tbody>`).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Partial page updates | Custom JS fetch + DOM manipulation | HTMX `hx-get` + `hx-target` + `hx-swap` | Battle-tested, no JS to maintain |
| Query string handling | Manual string parsing | FastAPI `Query()` parameters | Type-safe, automatic validation |
| Template inheritance | Copy-paste HTML | Jinja2 `{% extends %}` + `{% block %}` + `{% include %}` | DRY, single source for layout |
| Date arithmetic | Manual datetime math | Python `date` subtraction (returns `timedelta`) | Built-in, handles edge cases |

## Common Pitfalls

### Pitfall 1: Status computed inconsistently
**What goes wrong:** Dashboard stats show different counts than the table because status is computed in different places with different logic.
**Why it happens:** Copy-pasting status logic instead of using a single service function.
**How to avoid:** Single `get_license_status()` function in `app/services/status.py` used everywhere.
**Warning signs:** Stats counters don't match the visible rows in the table.

### Pitfall 2: HTMX filter state lost on sort
**What goes wrong:** User filters by product, then clicks sort -- the filter is lost because the sort link doesn't include the current filter values.
**Why it happens:** Sort links have hardcoded URLs without the current filter query params.
**How to avoid:** Use `hx-include` on sort headers to include all filter input values in the request.
**Warning signs:** Clicking a column header resets the filter dropdown/text input.

### Pitfall 3: Empty table on first visit
**What goes wrong:** Dashboard crashes or shows an ugly error when there are zero licenses in the DB.
**Why it happens:** Template assumes at least one license exists, or divides by zero in stats.
**How to avoid:** Handle empty state explicitly -- show a friendly "No licenses added yet" message. Guard against zero-division in percentage calculations.
**Warning signs:** Error on fresh database with no license records.

### Pitfall 4: Threshold not falling back correctly
**What goes wrong:** Licenses with `notify_days_before = NULL` show wrong status because the global threshold isn't fetched.
**Why it happens:** Forgetting the fallback chain: per-license -> DB setting -> env -> hardcoded 60.
**How to avoid:** `get_global_threshold(db)` function that implements the full chain. Use `lic.notify_days_before or global_threshold`.
**Warning signs:** All licenses show "active" even when expiring within 60 days.

### Pitfall 5: Sort direction toggle not working
**What goes wrong:** Clicking the same column header always sorts ascending, never toggling to descending.
**Why it happens:** The sort header always sends `order=asc` with no state tracking.
**How to avoid:** Pass current sort/order to the template, toggle direction in `hx-get` URL based on current state. Alternatively, use a hidden input for order state.
**Warning signs:** No way to sort descending.

### Pitfall 6: `hx-include` selector mismatches
**What goes wrong:** HTMX sends empty filter values because CSS selectors in `hx-include` don't match actual input names.
**Why it happens:** Typo in selector or renaming inputs without updating `hx-include`.
**How to avoid:** Use consistent `name` attributes and test with browser dev tools Network tab.
**Warning signs:** Server receives empty query params despite filled-in filter fields.

## Code Examples

### Dashboard Route (full page)

```python
@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: SessionDep):
    global_threshold = get_global_threshold(db)
    licenses = db.query(License).all()
    enriched = enrich_licenses(licenses, global_threshold)

    # Stats
    total = len(enriched)
    expiring = sum(1 for e in enriched if e["status"] == "warning")
    expired = sum(1 for e in enriched if e["status"] == "expired")

    # Expiring soon widget (top N by days remaining, warning only)
    expiring_soon = sorted(
        [e for e in enriched if e["status"] == "warning"],
        key=lambda e: e["days_remaining"],
    )[:10]

    # Default sort: expiry_date ascending
    sorted_licenses = sorted(enriched, key=lambda e: e["license"].expiry_date)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "total": total,
            "expiring": expiring,
            "expired": expired,
            "expiring_soon": expiring_soon,
            "licenses": sorted_licenses,
        },
    )
```

### Table Partial Route (HTMX fragment)

```python
@router.get("/licenses/table", response_class=HTMLResponse)
def license_table(
    request: Request,
    db: SessionDep,
    product: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    sort: str = Query("expiry_date"),
    order: str = Query("asc"),
):
    global_threshold = get_global_threshold(db)
    query = db.query(License)

    # Filter by product name (case-insensitive LIKE)
    if product:
        query = query.filter(License.product_name.ilike(f"%{product}%"))

    licenses = query.all()
    enriched = enrich_licenses(licenses, global_threshold)

    # Filter by computed status
    if status:
        enriched = [e for e in enriched if e["status"] == status]

    # Sort
    sort_key_map = {
        "expiry_date": lambda e: e["license"].expiry_date,
        "product_name": lambda e: e["license"].product_name.lower(),
    }
    sort_fn = sort_key_map.get(sort, sort_key_map["expiry_date"])
    enriched.sort(key=sort_fn, reverse=(order == "desc"))

    return templates.TemplateResponse(
        request=request,
        name="partials/license_table.html",
        context={
            "licenses": enriched,
            "current_sort": sort,
            "current_order": order,
        },
    )
```

### CSS Status Classes

```css
/* Status row colors */
.status-expired { background-color: #fce4e4; }     /* light red */
.status-expired:hover { background-color: #f8cccc; }
.status-warning { background-color: #fff8e1; }      /* light amber */
.status-warning:hover { background-color: #ffecb3; }
.status-active { background-color: #e8f5e9; }       /* light green */
.status-active:hover { background-color: #c8e6c9; }

/* Stats cards */
.stats-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
    margin-bottom: 2rem;
}
.stat-card {
    background: white;
    border-radius: 8px;
    padding: 1.5rem;
    text-align: center;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
.stat-card .count { font-size: 2rem; font-weight: bold; }
.stat-card .label { color: #666; margin-top: 0.5rem; }
.stat-card.expired .count { color: #d32f2f; }
.stat-card.warning .count { color: #f57f17; }
.stat-card.total .count { color: #1565c0; }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| jQuery AJAX for partial updates | HTMX declarative attributes | 2020+ | No custom JS needed |
| Separate API + SPA | Server-rendered HTML + HTMX | 2021+ | Simpler stack, no build step |
| Manual `request.headers["HX-Request"]` check | Separate partial endpoint (D-12) | N/A | Cleaner routing, avoids conditional logic in one route |

**Note on HTMX partial detection:** The project decisions specify separate routes (`GET /` for full page, `GET /licenses/table` for partial). This is cleaner than checking the `HX-Request` header in a single route. Follow this decision.

## Open Questions

1. **Exact number of licenses in expiring-soon widget**
   - What we know: D-06 says "top 5-10"
   - What's unclear: Exact limit
   - Recommendation: Use 10 (shows more context, easily adjustable). This is within Claude's discretion.

2. **Table column ordering**
   - What we know: License model has: product_name, purchase_date, expiry_date, responsible, cost, comment, notify_days_before
   - What's unclear: Which columns to show and in what order
   - Recommendation: Show product_name, expiry_date, days_remaining (computed), status (computed), responsible. Hide cost/comment/purchase_date from main table (save for detail page in Phase 3). This is within Claude's discretion.

3. **Sort direction toggle UX**
   - What we know: D-10 says sort by expiry_date (asc/desc) and product_name (asc/desc)
   - What's unclear: How to toggle direction in the UI
   - Recommendation: Clickable column headers that toggle asc/desc. Pass current sort state to template, generate toggled URL. Arrow indicator showing current direction.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | none (uses defaults) |
| Quick run command | `pytest tests/ -x -v` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DASH-01 | Stats counters on main page | integration | `pytest tests/test_dashboard.py::test_stats_counters -x` | No -- Wave 0 |
| DASH-02 | Expiring-soon widget visible | integration | `pytest tests/test_dashboard.py::test_expiring_soon_widget -x` | No -- Wave 0 |
| DASH-03 | Color-coded table rows | integration | `pytest tests/test_dashboard.py::test_status_color_classes -x` | No -- Wave 0 |
| DASH-04 | Filter/sort via HTMX partial | integration | `pytest tests/test_dashboard.py::test_table_filter_sort -x` | No -- Wave 0 |
| LIC-05 | Status computed from dates | unit | `pytest tests/test_status.py -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -v`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_status.py` -- unit tests for `days_until_expiry()`, `get_license_status()`, `get_global_threshold()`
- [ ] `tests/test_dashboard.py` -- integration tests for `GET /` and `GET /licenses/table` with test data
- [ ] Update `tests/conftest.py` -- add fixtures for creating test License records with various expiry dates

## Sources

### Primary (HIGH confidence)
- Project codebase -- `app/models.py`, `app/database.py`, `app/routers/pages.py`, `templates/base.html`, `static/css/app.css`
- `requirements.txt` -- verified pinned versions
- `.planning/phases/02-dashboard/02-CONTEXT.md` -- locked decisions D-01 through D-12
- HTMX official examples -- https://htmx.org/examples/sortable/

### Secondary (MEDIUM confidence)
- FastAPI with HTMX partials pattern -- https://www.angelospanag.me/blog/fastapi-with-htmx-partials
- HTMX table sorting and filtering patterns -- https://vladkens.cc/htmx-table-sorting/
- FastAPI + HTMX + Jinja2 hypermedia pattern -- https://testdriven.io/blog/fastapi-htmx/

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already installed and verified in project
- Architecture: HIGH -- patterns well-established, decisions locked in CONTEXT.md
- Pitfalls: HIGH -- common HTMX gotchas are well-documented in community

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (stable stack, no moving parts)
