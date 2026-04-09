# Phase 3: License CRUD - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

CRUD operations for licenses through the web interface: add, edit, delete licenses via forms, plus a license detail page. No notification logic, no settings — those are Phase 4. No new dashboard features beyond what Phase 2 delivered.

</domain>

<decisions>
## Implementation Decisions

### Add/Edit Form UX
- **D-01:** Add license via a dedicated page `GET /licenses/new` with a full form (all License model fields).
- **D-02:** Edit license via a dedicated page `GET /licenses/{id}/edit` — same form template as Add, pre-filled with current values. Reuse one template with conditionals for add vs edit mode.
- **D-03:** After successful save (create or edit), redirect back to the dashboard (`/`). No intermediate detail page or success toast.
- **D-04:** "Add license" button placed above the license table on the dashboard, near the filter controls.

### Delete Confirmation
- **D-05:** Delete uses HTMX `hx-delete` with `hx-confirm` attribute — browser native `confirm()` dialog showing the license product name.
- **D-06:** After successful deletion, the table row disappears (HTMX swap removes the `<tr>`). Stats counters update accordingly (via OOB swap or table partial reload).

### Claude's Discretion
- Detail page layout and design (DASH-05) — card layout, what fields to show, breadcrumb style
- Validation feedback approach — inline per-field errors vs summary banner
- Date input UX — native HTML date picker vs custom
- Form field ordering and grouping
- Edit/Delete action buttons placement in the table (icons vs text)
- Whether to add an "Edit" link on the detail page
- How to handle the "license not found" edge case (404 page vs redirect)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project requirements
- `.planning/PROJECT.md` — Project context, stack decisions, constraints
- `.planning/REQUIREMENTS.md` — Requirements LIC-01, LIC-02, LIC-03, DASH-05
- `.planning/ROADMAP.md` — Phase 3 success criteria and plan breakdown
- `CLAUDE.md` — Coding conventions (sync def routes, HTMX fragments, html.escape for Telegram, etc.)

### Prior phase context
- `.planning/phases/01-infrastructure/01-CONTEXT.md` — DB schema decisions (D-04..D-07: required/optional fields, cost as VARCHAR, date types)
- `.planning/phases/02-dashboard/02-CONTEXT.md` — Dashboard layout, HTMX partials pattern, status computation, Russian UI language

### Existing code
- `app/models.py` — License model (all fields), AppSettings model
- `app/database.py` — SessionDep, engine, Base
- `app/templates.py` — Jinja2Templates singleton
- `app/routers/pages.py` — Dashboard routes: `GET /` and `GET /licenses/table` (HTMX partial)
- `app/services/status.py` — `enrich_licenses()`, `get_global_threshold()`, `days_until_expiry()`
- `templates/base.html` — Base layout with HTMX 2.0.4, Russian nav
- `templates/index.html` — Dashboard page with stats, expiring-soon widget, license table
- `templates/partials/license_table.html` — Table rows partial (HTMX target)
- `static/css/app.css` — Existing styles (nav, stats cards, status colors, table)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/templates.py` — Jinja2Templates singleton, reuse in new license router
- `app/database.py` — `SessionDep` dependency for DB session injection
- `app/services/status.py` — `enrich_licenses()` for computing status on detail page
- `templates/base.html` — Base template to extend for form and detail pages
- `templates/partials/license_table.html` — Table row template to add Edit/Delete action columns

### Established Patterns
- Sync `def` routes for all DB-touching endpoints (per CLAUDE.md)
- `templates.TemplateResponse(request=request, name=...)` for rendering
- HTMX partials: server returns HTML fragments, client swaps `<tbody>` or `<tr>`
- Router registration via `app.include_router()` in `main.py`
- Filter controls use `hx-get`, `hx-target`, `hx-include` for partial updates

### Integration Points
- `app/main.py` — register new license CRUD router
- `templates/index.html` — add "Add license" button above table, add Edit/Delete columns to table
- `templates/base.html` — potentially add nav links (Licenses, Add)
- `templates/partials/license_table.html` — add action buttons per row

</code_context>

<specifics>
## Specific Ideas

- Form pages should follow the same single-column layout as the dashboard
- Russian labels for all form fields (consistent with Phase 2 UI language)
- The roadmap plans 03-01/02/03 already outline the route structure — respect that decomposition

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-license-crud*
*Context gathered: 2026-04-09*
