---
gsd_state_version: 1.0
milestone: v1.0.1
milestone_name: hardening
status: Hardening commits applied — UI redesign and v1.1 pending
last_updated: "2026-05-04T00:00:00.000Z"
progress:
  total_phases: 5
  completed_phases: 5
  total_plans: 17
  completed_plans: 17
---

# Project State

## Current Status

**Milestone:** v1.0.1 (hardening) applied on top of v1.0  
**Status:** Critical fixes shipped. UI redesign + v1.1 (SSL/support entities) planned.

## Phase Progress

| Phase | Status |
|-------|--------|
| Phase 1 — Infrastructure | ✅ |
| Phase 2 — Dashboard | ✅ |
| Phase 3 — License CRUD | ✅ |
| Phase 03.1 — UI Polish | ✅ |
| Phase 4 — Notifications & Settings | ✅ (UAT 2026-04-30) |

## v1.0.1 Hardening (2026-05-04)

Senior-engineer audit fixes:
- **Security:** Telegram secrets removed from DB and Settings UI. Source of truth = `.env`. Legacy `telegram_*` rows purged on bootstrap.
- **Telegram:** `parse_mode=HTML` added — fixes `&amp;` literal display bug.
- **Container:** non-root user (`app:1000`) via `gosu` entrypoint. `tzdata` installed.
- **Time:** `TZ=Asia/Almaty` propagated through compose env, APScheduler timezone-aware (`ZoneInfo(TZ)` on `BackgroundScheduler` + `CronTrigger`).
- **Errors:** Bare `except Exception: pass` in settings router replaced with `JobLookupError` + logging.
- **Validation:** Form-level positive-int check on `notify_days_before` in license create/update.
- Tests: 140 passed, 1 skipped. test_settings/scheduler/models rewritten for new contract.

## Pending

1. **Phase 5 — UI redesign** (общий редизайн, separate phase)
2. **Phase 6 — Refactor** (repository layer, Pydantic schemas, multi-stage Dockerfile, money type) — фундамент под v1.1
3. **Phase 7 — v1.1 entities** (SSL certificates, support contracts) — после рефакторинга
4. **Final** — Keycloak/OIDC auth, production hardening (nginx, HTTPS, backup)

## Next Action

Awaiting user decision on Phase 5 (UI redesign) scope.
