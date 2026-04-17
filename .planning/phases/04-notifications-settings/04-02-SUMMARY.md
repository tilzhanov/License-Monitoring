---
phase: 04-notifications-settings
plan: 02
subsystem: notifications
tags: [telegram, httpx, html-escape, digest, unit-tests, mock]

requires:
  - phase: 04-01-settings
    provides: AppSettings model with bot_token/chat_id/notify_days_before keys
  - phase: 03-license-crud
    provides: License model with notify_days_before per-license override field
  - phase: 02-dashboard
    provides: status.py enrich_licenses() and get_global_threshold()

provides:
  - send_telegram_message() — sync httpx.Client POST to Bot API with error classification
  - format_license_line() — single-license bullet line per D-03 with html.escape
  - format_digest() — urgency-tiered digest (D-01, D-02, D-04) returning None if empty

affects:
  - 04-03-scheduler
  - 04-04-test-notification

tech-stack:
  added: []
  patterns:
    - "Sync httpx.Client context manager for Bot API calls (not async)"
    - "html.escape() on all user strings before Telegram output"
    - "Return None from format_digest when no qualifying licenses (D-04)"
    - "unittest.mock.patch + MagicMock context manager for httpx mocking"

key-files:
  created:
    - app/services/telegram.py
    - tests/test_telegram.py
  modified: []

key-decisions:
  - "No parse_mode in sendMessage payload — plain text per D-03 (not HTML mode)"
  - "httpx.TimeoutException caught separately before generic HTTPError"
  - "format_license_line uses bullet character U+2022, not asterisk"
  - "Responsible field omitted when None/empty — no trailing em-dash"

patterns-established:
  - "Telegram error code to Russian message mapping via _ERROR_MESSAGES dict"
  - "Enriched item dict structure: {license, days_remaining, status, status_class}"
  - "format_digest sections: red-circle expired header then yellow-circle warning header"

requirements-completed:
  - NOTF-01
  - NOTF-03
  - NOTF-05

duration: 8min
completed: 2026-04-17
---

# Phase 4 Plan 02: Telegram Notification Service Summary

**Telegram service with sync httpx.Client, urgency-tiered Russian digest (D-01..D-04), html.escape safety, and 15 unit tests with full mocking**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-17T04:57:00Z
- **Completed:** 2026-04-17T04:57:21Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- `send_telegram_message()` sends POST to Bot API, maps 401/400/403/429 to Russian errors, handles timeout and generic HTTP errors
- `format_digest()` groups licenses into expired and warning sections with emoji headers, returns None for empty/all-active lists per D-04
- `format_license_line()` produces bullet-prefixed lines with DD.MM.YYYY date, days count, and optional responsible — all user strings html.escape'd
- 15 unit tests cover all branches: success, 4 error codes, timeout, HTTP error, empty digest, urgency grouping, HTML escaping, responsible None case

## Task Commits

1. **Task 1: Telegram service implementation** - `11bcaad` (feat)
2. **Task 2: Telegram service unit tests** - `b8434d5` (test)

## Files Created/Modified

- `app/services/telegram.py` — Telegram send + digest formatting service (97 lines)
- `tests/test_telegram.py` — 15 unit tests with httpx mocking (265 lines)

## Decisions Made

- No `parse_mode` in sendMessage payload — D-03 specifies plain text, future-proofing via html.escape is still applied
- `httpx.TimeoutException` caught before generic `httpx.HTTPError` so timeout gets specific Russian message
- `format_license_line` uses U+2022 bullet (`•`) not asterisk — per plan spec, verified by test assertion
- Responsible field: when None or empty, trailing ` — ` separator is omitted entirely (strip trailing space)

## Deviations from Plan

None - plan executed exactly as written. Added `test_send_telegram_http_error` and `test_format_digest_only_expired/only_warning` beyond the 10 specified — these cover edge cases in existing functions and improve branch coverage (Rule 2: missing critical coverage, low impact).

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required for this plan (service is a pure Python module, no DB or runtime config needed at this stage).

## Next Phase Readiness

- `app/services/telegram.py` is importable and fully tested — ready for Plan 03 (scheduler) to call `send_telegram_message` and `format_digest`
- Plan 04 (test-notification button) can call `send_telegram_message` directly from the router

---
*Phase: 04-notifications-settings*
*Completed: 2026-04-17*
