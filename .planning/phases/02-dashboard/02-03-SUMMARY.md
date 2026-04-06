---
phase: 02-dashboard
plan: 03
subsystem: ui
tags: [htmx, jinja2, filtering, sorting, integration-tests, fastapi]

requires:
  - phase: 02-dashboard/02-01
    provides: status computation service (enrich_licenses, get_global_threshold)
  - phase: 02-dashboard/02-02
    provides: dashboard page with stats, expiring widget, and license table
provides:
  - HTMX-powered filter/sort on license table without full page reload
  - GET /licenses/table partial endpoint returning filtered/sorted tbody rows
  - Integration test suite covering all Phase 2 dashboard requirements
affects: [03-license-crud]

tech-stack:
  added: []
  patterns: [HTMX partial endpoint pattern, hx-include for cross-control state preservation]

key-files:
  created: [tests/test_dashboard.py]
  modified: [app/routers/pages.py, templates/index.html]

key-decisions:
  - "Sort state tracked via hidden inputs; sort headers use URL params and hx-include for filter values only"
  - "Per-test DB cleanup via autouse fixture with dependency override restore to avoid cross-module test conflicts"

patterns-established:
  - "HTMX partial pattern: endpoint returns Jinja2 template fragment, swapped into target via hx-get/hx-target"
  - "Filter+sort state preservation: hx-include selects complementary controls to send all state with each request"
  - "Integration test pattern: StaticPool in-memory SQLite, per-test cleanup, fixture-scoped dependency override"

requirements-completed: [DASH-04]

duration: 5min
completed: 2026-04-06
---

# Phase 02 Plan 03: Filters & Sorting Summary

**HTMX-powered filter by product/status and sort by expiry_date/product_name on license table with 14 integration tests covering DASH-01 through DASH-04**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-06T09:55:55Z
- **Completed:** 2026-04-06T10:01:30Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- HTMX partial endpoint GET /licenses/table with product, status, sort, and order query params
- Filter controls (text input with keyup debounce, status dropdown) and sortable column headers wired with hx-get/hx-target/hx-include
- 14 integration tests covering: empty state, stats counters (DASH-01), expiring widget (DASH-02), color-coded rows (DASH-03), filter/sort via HTMX partial (DASH-04)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add HTMX table partial endpoint and wire filter/sort controls** - `b4c7816` (feat)
2. **Task 2: Create integration tests for dashboard routes** - `9d66cab` (test)

## Files Created/Modified
- `app/routers/pages.py` - Added GET /licenses/table endpoint with filter/sort params
- `templates/index.html` - Wired HTMX attributes on filter controls and sortable column headers
- `tests/test_dashboard.py` - 14 integration tests covering all Phase 2 requirements

## Decisions Made
- Sort state tracked via hidden inputs updated on full page load; sort headers encode sort/order in URL params and use hx-include only for filter values to avoid param duplication
- Integration tests use per-fixture dependency override with restore (not module-level clear) to avoid conflicts with test_health.py module-level override
- Sort by product_name uses lowercase comparison for consistent case-insensitive ordering

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test sort order assertion**
- **Found during:** Task 2 (integration tests)
- **Issue:** Test assumed alphabetical order veeam < vcenter < vcloud, but lowercase sort gives vcenter < vcloud < veeam (vc < vc < ve)
- **Fix:** Corrected assertion to match actual lowercase alphabetical sort
- **Files modified:** tests/test_dashboard.py
- **Verification:** All 14 tests pass
- **Committed in:** 9d66cab (Task 2 commit)

**2. [Rule 3 - Blocking] Fixed cross-module test dependency override conflict**
- **Found during:** Task 2 (full suite run)
- **Issue:** Module-level app.dependency_overrides.clear() in client fixture removed test_health.py's override, causing subsequent tests to fail with sqlite3.OperationalError
- **Fix:** Changed to per-fixture override with restore of previous value instead of clear()
- **Files modified:** tests/test_dashboard.py
- **Verification:** Full suite (49 tests) passes
- **Committed in:** 9d66cab (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both fixes necessary for test correctness. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviations above.

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all filter/sort functionality is fully wired to the backend endpoint.

## Next Phase Readiness
- Phase 02 (Dashboard) is complete with all requirements DASH-01 through DASH-04 delivered
- License table with HTMX filter/sort ready for Phase 03 (License CRUD) to add create/edit/delete actions
- Integration test patterns established for reuse in Phase 03 tests

---
*Phase: 02-dashboard*
*Completed: 2026-04-06*
