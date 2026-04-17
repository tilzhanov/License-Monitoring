---
phase: 04-notifications-settings
plan: 03
subsystem: scheduler
tags: [apscheduler, cron, daily-digest, telegram, lifespan, tdd]
dependency_graph:
  requires: [04-02]
  provides: [daily-digest-scheduler, scheduler-lifecycle, reschedule-on-settings-save]
  affects: [app/main.py, app/routers/settings.py]
tech_stack:
  added: []
  patterns: [BackgroundScheduler-in-lifespan, Session(engine)-in-thread, CronTrigger-reschedule]
key_files:
  created:
    - app/services/scheduler.py
    - tests/test_scheduler.py
  modified:
    - app/main.py
    - app/routers/settings.py
decisions:
  - "Session(engine) used directly in scheduler job (not request-scoped get_session) for thread-safety"
  - "scheduler.running guard prevents SchedulerAlreadyRunningError on uvicorn --reload"
  - "reschedule_digest wrapped in try/except in settings router to handle test environments"
  - "last_digest_sent stored in AppSettings only on successful send"
metrics:
  duration: "1m 47s"
  completed_date: "2026-04-17"
  tasks_completed: 2
  files_created: 2
  files_modified: 2
---

# Phase 4 Plan 3: APScheduler Daily Digest Summary

**One-liner:** APScheduler BackgroundScheduler wired into FastAPI lifespan with CronTrigger daily digest that queries licenses, formats Telegram message, and reschedules when settings change.

## What Was Built

### `app/services/scheduler.py` (new)

Module-level `BackgroundScheduler` singleton with four exported functions:

- `send_daily_digest()` — Scheduled job. Creates `Session(engine)` directly (thread-safe, not request-scoped). Reads `telegram_bot_token` + `telegram_chat_id` from AppSettings; silently returns if either is missing (D-11). Calls `get_global_threshold()`, queries all licenses, calls `enrich_licenses()` + `format_digest()`. Sends via `send_telegram_message()`. On successful send, upserts `last_digest_sent` ISO timestamp in AppSettings.

- `init_scheduler(hour, minute)` — Adds `daily_digest` job with `CronTrigger(hour, minute)`, `replace_existing=True`, `misfire_grace_time=3600`. Guards with `if not scheduler.running` before calling `start()`.

- `reschedule_digest(hour, minute)` — Calls `scheduler.reschedule_job("daily_digest", trigger=CronTrigger(...))` for D-07 live rescheduling.

- `shutdown_scheduler()` — Calls `scheduler.shutdown(wait=False)` if running.

### `app/main.py` (modified)

Lifespan now reads `notify_time` from AppSettings (falls back to `"09:00"`), parses `HH:MM`, calls `init_scheduler(hour, minute)` after `bootstrap_settings()`, and calls `shutdown_scheduler()` after `yield`.

### `app/routers/settings.py` (modified)

POST `/settings` handler now calls `reschedule_digest(h, m)` after saving `notify_time`, wrapped in `try/except` to handle test environments where scheduler is not running.

### `tests/test_scheduler.py` (new — 9 tests)

| Test | Behavior Verified |
|------|-------------------|
| `test_init_scheduler_starts` | add_job called with id="daily_digest"; start() called |
| `test_init_scheduler_no_double_start` | start() NOT called when scheduler.running=True |
| `test_reschedule_digest` | reschedule_job("daily_digest", CronTrigger) called |
| `test_send_daily_digest_skips_no_token` | Returns early when bot_token empty (D-11) |
| `test_send_daily_digest_skips_no_chat_id` | Returns early when chat_id empty (D-11) |
| `test_send_daily_digest_skips_empty_digest` | send_telegram_message not called when no qualifying licenses (D-04) |
| `test_send_daily_digest_sends_message` | send_telegram_message called with token, chat_id, non-empty string |
| `test_send_daily_digest_updates_last_sent_timestamp` | last_digest_sent stored in AppSettings on success |
| `test_send_daily_digest_no_timestamp_on_failed_send` | last_digest_sent NOT stored when Telegram returns error |

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | a02d49c | feat(04-03): implement APScheduler daily digest and lifespan wiring |
| Task 2 | 2ae759e | test(04-03): add 9 scheduler unit tests for digest lifecycle |

## Deviations from Plan

### Auto-additions (Rule 2 — Missing Critical Functionality)

**1. [Rule 2 - Enhancement] Two additional tests beyond minimum 7**

- **Found during:** Task 2
- **Decision:** Added `test_send_daily_digest_updates_last_sent_timestamp` and `test_send_daily_digest_no_timestamp_on_failed_send` to cover the `last_digest_sent` timestamp behavior implemented in the scheduler. The plan mentioned the timestamp as a "discretion item" in Task 1, so testing it was the correct completion.
- **Files modified:** tests/test_scheduler.py
- **Result:** 9 tests instead of minimum 7 — all pass

None other. Plan executed as written with one additive deviation (more tests).

## Test Results

```
pytest tests/test_scheduler.py -v  →  9 passed
pytest tests/ -x -q               →  134 passed (0 failures)
```

## Known Stubs

None. The scheduler fully wires into the lifespan and settings router. `last_digest_sent` is populated on first successful send (empty until then — by design, not a stub).

## Self-Check: PASSED
