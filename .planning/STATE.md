---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: catalog
status: Catalog (vendor → product → asset) shipped. SSL feature removed. License + support only. v1.1.1 fixes deployed 2026-08-13.
last_updated: "2026-08-13T00:00:00.000Z"
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

## v1.1.1 Fixes (2026-08-13)

- **500 on assets without a purchase date.** `license_detail.html` and `license_form.html` called `.strftime()` / `.isoformat()` on the nullable `purchase_date`, so `/licenses/{id}` and `/licenses/{id}/edit` died for the 12 of 18 production assets created through the catalog.
- **Validation aligned.** The legacy `_validate_license_form` demanded a purchase date that the model, the catalog validator and the form markup all already treated as optional.
- `CLAUDE.md` rewritten around what the repo cannot tell you; `SENIOR_ENGINEER.md` and `TOKEN_GUIDE.md` removed.
- Network wiring moved out of the host's uncommitted `docker-compose.yml` edit into `docker-compose.prod.yml`.
- Tests: 151 passed, 1 skipped.

## Deployment

The host runs 13 other services behind a shared `nginx-proxy`. Keep commands inside the project folder, and never prune Docker globally.

**The host reaches neither GitHub nor the Debian apt mirrors.** Two consequences, each of which cost a session to find:

- `git pull` fails — no deploy key. Commits travel by bundle: `git bundle create f.bundle <old>..master` locally, copy it over, then `git pull --ff-only f.bundle master` on the host.
- `docker compose build` dies on the `apt-get install tzdata gosu` layer whenever the build cache has expired. Build on a machine with internet (`docker build -t license-monitoring-web:latest .`), ship it via `docker save | gzip` → `docker load`, then `docker compose up -d --no-build`.

The build cache on that host is shared with every other service on the box, so pruning it strands them all on the same apt failure.

Network wiring lives in `docker-compose.prod.yml`, tracked in git and switched on by `COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml` in the host's own `.env` (documented in `.env.example`). That line is load-bearing: drop it and the container leaves `proxy-network`, and nginx loses sight of it.

## Pending

1. **Phase 6 — Refactor** (repository layer, Pydantic schemas, multi-stage Dockerfile, money type)
2. **Final** — Keycloak/OIDC auth, production hardening (nginx, HTTPS, backup)

## Next Action

Awaiting user decision on next milestone scope.

Two items surfaced during the 2026-08-13 deploy and are still open: the host has no deploy key for GitHub and no reachable apt mirror, which is what forces the build-elsewhere-and-ship-the-image route above.
