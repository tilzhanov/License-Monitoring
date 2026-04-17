---
phase: 04-notifications-settings
plan: "04"
subsystem: settings-notifications
tags: [settings, telegram, per-license-threshold, htmx, tests]
dependency_graph:
  requires: [04-01, 04-02, 04-03]
  provides: [test-notification-endpoint, per-license-threshold-field]
  affects: [app/routers/settings.py, app/routers/licenses.py, templates/license_form.html]
tech_stack:
  added: []
  patterns: [inline-html-response, unittest.mock.patch]
key_files:
  created: []
  modified:
    - app/routers/settings.py
    - app/routers/licenses.py
    - templates/license_form.html
    - static/css/app.css
    - tests/test_settings.py
    - tests/test_licenses.py
decisions:
  - test_notification returns raw HTMLResponse (not template) for HTMX inline swap
  - notify_days_before parsed as int or None (empty string = global default)
  - Patching app.routers.settings.send_telegram_message (not app.services.telegram) for correct mock scope
metrics:
  duration: "~15 minutes"
  completed: "2026-04-17"
  tasks_completed: 2
  tasks_pending: 1
  files_changed: 6
---

# Phase 04 Plan 04: Test Notification & Per-License Threshold Summary

**One-liner:** POST /settings/test-notification sends inline HTMX result; notify_days_before field wired through license forms to DB with None fallback for global default.

## Tasks Completed

### Task 1: Test notification endpoint and per-license threshold field
**Commit:** `fafb7a2`

- Added `POST /settings/test-notification` to `app/routers/settings.py` — reads token/chat_id from DB, calls `send_telegram_message`, returns inline HTML fragment (alert-success or alert-error)
- Verified `templates/settings.html` already had correct `hx-post`, `hx-target="#test-result"`, `hx-swap="innerHTML"` — no changes needed
- Added `notify_days_before` number field to `templates/license_form.html` (after comment, before form-actions) with placeholder "По умолчанию: глобальный порог" and `.field-hint` helper text
- Updated `create_license()` and `update_license()` in `app/routers/licenses.py` to accept `notify_days_before: str = Form("")`, parse to int or None, save to model
- Added `.field-hint` CSS rule to `static/css/app.css`

### Task 2: Integration tests for test notification and per-license threshold
**Commit:** `6948614`

- Added 3 tests to `tests/test_settings.py` (SETT-02):
  - `test_test_notification_success` — patches send_telegram_message, verifies success message
  - `test_test_notification_no_credentials` — empty DB, verifies "Сначала настройте" error
  - `test_test_notification_telegram_error` — patches with error dict, verifies "Ошибка" + message
- Added 4 tests to `tests/test_licenses.py` (LIC-06, D-13):
  - `test_create_license_with_threshold` — POST with notify_days_before=45, DB confirms value
  - `test_create_license_without_threshold` — POST without field, DB confirms None
  - `test_edit_license_threshold_field_rendered` — GET edit page, asserts field present
  - `test_update_license_with_threshold` — POST update with 90, DB confirms value

**Full test suite: 141 tests pass** (was 134 before this plan, +7 new tests)

## Tasks Pending Human Verification

### Task 3: Visual and functional UAT (checkpoint:human-verify)
**Status:** PENDING — requires human to start Docker stack and verify UI

See checkpoint details below for verification steps.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all functionality is wired end-to-end. The test notification endpoint calls the real `send_telegram_message` function (mocked only in tests).

## Self-Check: PASSED

- `fafb7a2` exists in git log
- `6948614` exists in git log
- `app/routers/settings.py` contains `def test_notification`
- `templates/license_form.html` contains `notify_days_before` (3 occurrences)
- `app/routers/licenses.py` contains `notify_days_before` (9 occurrences)
- 141 tests pass
