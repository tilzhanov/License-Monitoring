---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: catalog
status: Catalog (vendor → product → asset) shipped. SSL feature removed. License + support only.
last_updated: "2026-05-06T00:00:00.000Z"
progress:
  total_phases: 5
  completed_phases: 5
  total_plans: 17
  completed_plans: 17
---

# Project State

## Current Status

**Milestone:** v1.1 (catalog) on top of v1.0.1 hardening
**Status:** Vendor → Product → Asset catalog live. Asset types: **license, support** (SSL dropped per stakeholder request 2026-05-06). SLA field on support assets dropped same day. Money formatting (thousands separator + ₸) on detail page. Asset name in product detail clickable. Asset creation funneled through catalog (dashboard "Добавить лицензию" → "Добавить через каталог").

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

## v1.1 Catalog Iterations (2026-05-06)

- Asset-type filter dropdown on dashboard table (license / support).
- Product detail: clickable asset name → `/licenses/{id}` detail page.
- License detail: `cost` rendered via `money` Jinja filter — thin-space thousands separator + `₸`.
- "Добавить лицензию" button on dashboard removed; replaced with "Добавить через каталог" (forces vendor/product context).
- **SSL feature removed** entirely: `ASSET_TYPE_SSL`, `ssl_domain`, `ssl_issuer` columns unmapped on ORM. Startup migration `_purge_ssl_assets()` deletes legacy `asset_type='ssl'` rows. Columns kept in SQLite schema (no DROP COLUMN — ORM ignores).
- **SLA field removed** from support assets (`support_sla` unmapped, form/template/telegram refs stripped).
- Tests: 148 passed.

## Pending

1. **Phase 6 — Refactor** (repository layer, Pydantic schemas, multi-stage Dockerfile, money type)
2. **Final** — Keycloak/OIDC auth, production hardening (nginx, HTTPS, backup)

## Next Action

Awaiting user decision on next milestone scope.
