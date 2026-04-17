---
phase: 04-notifications-settings
plan: "01"
subsystem: settings
tags: [settings, htmx, forms, db-persistence, telegram-config]
dependency_graph:
  requires: []
  provides: [settings-page, settings-router, db-settings-persistence]
  affects: [notifications, scheduler]
tech_stack:
  added: []
  patterns: [htmx-outerhtml-swap, db-over-env-precedence, sync-def-routes]
key_files:
  created:
    - app/routers/settings.py
    - templates/settings.html
    - templates/partials/settings_form.html
    - tests/test_settings.py
  modified:
    - templates/base.html
    - app/main.py
    - static/css/app.css
decisions:
  - "notify_time stored as HH:MM string in AppSettings; validated server-side with regex"
  - "get_setting helper returns DB value if non-empty, else env fallback (SETT-03 DB-over-env)"
  - "POST /settings returns partials/settings_form.html fragment (HTMX outerHTML swap on #settings-form)"
  - "Test notification button wired in settings.html with hx-post=/settings/test-notification; endpoint implemented in Plan 04"
metrics:
  duration_minutes: 12
  completed_date: "2026-04-17"
  tasks_completed: 2
  files_created: 4
  files_modified: 3
---

# Phase 04 Plan 01: Settings Page Summary

Settings page with HTMX form for Telegram bot configuration (token, chat_id, notify_days_before, notify_time) persisted to AppSettings table with DB-over-env precedence.

## What Was Built

- `GET /settings` — renders settings form pre-filled from DB (falling back to env/hardcoded defaults)
- `POST /settings` — validates four fields, saves each to AppSettings via upsert, returns HTMX outerHTML fragment with success banner or field errors
- `templates/settings.html` — page extending `base.html` with test-notification button placeholder (wired in Plan 04)
- `templates/partials/settings_form.html` — `<div id="settings-form">` with `hx-post="/settings" hx-target="#settings-form" hx-swap="outerHTML"`
- Настройки nav link added to `templates/base.html`
- 7 integration tests covering render, save, persistence, validation (threshold + time), nav link, DB-precedence

## Validation

- `get_setting(db, key, fallback)` — queries AppSettings, returns `row.value` if found and non-empty, else fallback
- `save_setting(db, key, value)` — upserts row (query → update if exists, insert if not)
- `notify_days_before` must be a positive integer
- `notify_time` must match `^\d{2}:\d{2}$` with hour 0–23, minute 0–59

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed inline style from settings.html**
- **Found during:** Task 1 verification
- **Issue:** Plan specified `style="margin-top: var(--space-4);"` on the test-notification wrapper div, which violated the existing `test_ui18_all_templates_free_of_inline_styles` test (UI-18 constraint from Phase 03.1)
- **Fix:** Added `.settings-test-action { margin-top: var(--space-4); }` to `static/css/app.css`; replaced inline style with `class="settings-test-action"`
- **Files modified:** `templates/settings.html`, `static/css/app.css`
- **Commit:** 5df0a00

**2. [Rule 1 - Bug] Used `yield TestClient(app)` without context manager**
- **Found during:** Task 2 — test_settings.py ran with `with TestClient(app)`, which triggers lifespan and tries to open `/data/licenses.db`
- **Fix:** Changed to `yield TestClient(app)` (no `with`) to match the pattern in test_dashboard.py/test_licenses.py
- **Commit:** d03c4be

## Known Stubs

- Test-notification button on `templates/settings.html` targets `POST /settings/test-notification` which does not exist yet — will be implemented in Plan 04.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | 5df0a00 | feat(04-01): settings page with HTMX form and DB persistence |
| Task 2 | d03c4be | test(04-01): 7 integration tests for settings routes |

## Self-Check: PASSED

- [x] `app/routers/settings.py` — exists
- [x] `templates/settings.html` — exists
- [x] `templates/partials/settings_form.html` — exists
- [x] `tests/test_settings.py` — exists
- [x] Commit 5df0a00 — exists
- [x] Commit d03c4be — exists
- [x] 110/110 tests pass (no regressions)
