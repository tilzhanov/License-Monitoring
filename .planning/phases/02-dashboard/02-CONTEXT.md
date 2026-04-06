# Phase 2: Dashboard - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning
**Source:** Auto-generated from project requirements and Phase 1 context

<domain>
## Phase Boundary

Read-only dashboard showing the full state of all licenses at a glance: summary counters, expiring-soon widget, color-coded license table with filtering and sorting. No CRUD — that's Phase 3. No notifications — that's Phase 4.

</domain>

<decisions>
## Implementation Decisions

### Status Computation
- **D-01:** Status computed server-side from `expiry_date` and threshold. Three states: `active` (days > threshold), `warning` (0 < days <= threshold), `expired` (days <= 0).
- **D-02:** Threshold = per-license `notify_days_before` if set, else global default (60 days from `app_settings`).
- **D-03:** `days_until_expiry()` helper function in a new `app/services/status.py` module.

### Page Layout
- **D-04:** Single-column layout: stats counters at top, expiring-soon widget below, full license table at bottom.
- **D-05:** Stats counters: 3 cards — Total, Expiring Soon, Expired — each showing count.
- **D-06:** Expiring-soon widget: top 5-10 licenses sorted by days remaining ascending, showing product name, expiry date, days remaining.

### Color Coding (DASH-03)
- **D-07:** Table row CSS classes: `status-expired` (red), `status-warning` (yellow/amber), `status-active` (green). Applied server-side via Jinja2.

### Filtering and Sorting (DASH-04)
- **D-08:** HTMX-powered — filter/sort controls send GET requests, server returns HTML table fragment replacing `<tbody>`.
- **D-09:** Filter by: product name (text input), status (dropdown: all/active/warning/expired).
- **D-10:** Sort by: expiry date (asc/desc), product name (asc/desc). Default: expiry date ascending.

### Routes
- **D-11:** `GET /` — full dashboard page (stats + widget + table).
- **D-12:** `GET /licenses/table` — HTMX partial returning only `<tbody>` for filter/sort updates.

### Claude's Discretion
- Exact CSS colors and card styling (within the constraint of red/yellow/green for statuses)
- Empty state message when no licenses exist
- Exact number of licenses in expiring-soon widget
- Table column ordering
- Navigation bar additions

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project requirements
- `.planning/PROJECT.md` — Project context, stack decisions, constraints
- `.planning/REQUIREMENTS.md` — Requirements DASH-01 through DASH-04, LIC-05
- `.planning/ROADMAP.md` — Phase 2 success criteria and plan breakdown

### Phase 1 context
- `.planning/phases/01-infrastructure/01-CONTEXT.md` — DB schema decisions (D-04 through D-10), settings precedence

### Existing code
- `app/models.py` — License model with expiry_date, notify_days_before fields
- `app/database.py` — SessionDep, engine, bootstrap_settings
- `app/templates.py` — Jinja2Templates singleton
- `app/routers/pages.py` — Existing index route to extend
- `templates/base.html` — Base template with HTMX 2.0.4 CDN
- `static/css/app.css` — Existing CSS (nav, main, base typography)
- `CLAUDE.md` — Coding conventions (sync def routes, HTMX fragments, etc.)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/templates.py` — Jinja2Templates singleton, reuse in new routers
- `templates/base.html` — Base layout with HTMX 2.0.4 and nav bar
- `static/css/app.css` — Base styles (nav, main container, typography)
- `app/database.py` — SessionDep for dependency injection in routes

### Established Patterns
- Sync `def` routes for all DB-touching endpoints (per CLAUDE.md)
- `templates.TemplateResponse(request=request, name=...)` pattern
- HTMX loaded via CDN in base.html
- Router included via `app.include_router()` in main.py

### Integration Points
- `app/main.py` — include new routers here
- `templates/base.html` — extend for dashboard page
- `app/routers/pages.py` — existing index route (replace placeholder)
- `static/css/app.css` — extend with status colors and card styles

</code_context>

<specifics>
## Specific Ideas

- Dashboard is the main landing page — replaces current placeholder at `/`
- Language for UI: Russian (team is Russian-speaking, per project context)
- No JS build step — all interactivity via HTMX attributes

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-dashboard*
*Context gathered: 2026-04-06*
