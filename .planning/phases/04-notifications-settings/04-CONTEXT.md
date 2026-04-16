# Phase 4: Notifications & Settings - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Telegram alerting loop: daily digest fires automatically via APScheduler, sends urgency-tiered Telegram messages for licenses approaching expiry. Operators configure bot token, chat ID, global threshold, and notification time through a Settings page. Per-license threshold override is accessible via the edit form. No auth, no multi-chat, no email — all locked out of scope.

</domain>

<decisions>
## Implementation Decisions

### Digest Format
- **D-01:** Licenses grouped by urgency tiers: 🔴 Истекло / 🟡 Истекает скоро — two sections, emoji headers.
- **D-02:** Inclusion criteria: only licenses where `days_remaining ≤ global_threshold` OR expired (days ≤ 0). Active licenses not included.
- **D-03:** Format — Russian plain text, `parse_mode` not required. One line per license: `• ProductName — DD.MM.YYYY (N дней) — Responsible`. If responsible is null, omit that field.
- **D-04:** Empty digest (0 qualifying licenses) — send nothing. No "all clear" message.

### Scheduler Timing
- **D-05:** Default fire time: 09:00. Configurable via Settings UI — stored as `notify_time` key in `AppSettings` (value format: `"HH:MM"`).
- **D-06:** Timezone: controlled by `TZ` env var in Docker Compose — not a settings-page field.
- **D-07:** APScheduler `BackgroundScheduler` with `CronTrigger` started in FastAPI lifespan. Reschedule on settings save if time changes.

### Settings Page UX
- **D-08:** Single page `GET /settings` with one form — fields: `bot_token`, `chat_id`, `notify_days_before` (global threshold), `notify_time`.
- **D-09:** Single POST `/settings` save button: «Сохранить настройки». HTMX replaces form section on success/error — no full page reload.
- **D-10:** Test notification button: «Отправить тестовое уведомление» — `POST /settings/test-notification`. Result shown inline in `<div id="test-result">` below the button via HTMX swap.
- **D-11:** No scheduler enable/disable toggle — scheduler runs whenever `bot_token` + `chat_id` are configured; silently skips if either is missing.

### Per-License Threshold Field
- **D-12:** Placement: Claude's discretion — add form, edit form, or both. Field maps to `License.notify_days_before` (already in schema).
- **D-13:** Empty-field UX (global default): Claude's discretion — placeholder, helper text, or label annotation.

### Claude's Discretion
- Where `notify_days_before` override field appears (add form, edit form, both)
- Placeholder/helper text when field is empty (global default fallback)
- Exact HTML structure of Settings page (field grouping, label styles)
- Error message copy for Telegram API failures (401, 400, timeout)
- Whether to show last-sent timestamp on Settings page

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project foundation
- `CLAUDE.md` — Coding conventions: sync def routes, HTMX fragments, `html.escape()` for Telegram, settings precedence chain (DB→env→default)
- `.planning/PROJECT.md` — Stack decisions (APScheduler, one bot/one chat), constraints
- `.planning/REQUIREMENTS.md` — NOTF-01..NOTF-06, SETT-01..SETT-03, LIC-06, INFRA-04
- `.planning/ROADMAP.md` — Phase 4 success criteria and plan breakdown

### Prior phase context
- `.planning/phases/03-license-crud/03-CONTEXT.md` — Form patterns, HTMX partial patterns, routing conventions
- `.planning/phases/02-dashboard/02-CONTEXT.md` — HTMX partials, status computation, Russian UI language

### Existing code (MUST read before writing)
- `app/models.py` — `License` (has `notify_days_before`), `AppSettings` (key-value store)
- `app/services/status.py` — `get_global_threshold()` reads DB→env→60 fallback
- `app/config.py` — `NOTIFY_DAYS_BEFORE` env var, other config constants
- `app/routers/licenses.py` — CRUD router patterns (sync def, SessionDep, HTMX responses)
- `app/routers/pages.py` — Dashboard route pattern
- `app/templates.py` — Jinja2Templates singleton (do NOT re-instantiate in routers)
- `app/main.py` — Lifespan function (where APScheduler starts)
- `templates/base.html` — Nav structure (add Settings link here)
- `templates/license_form.html` — Existing form template (add override field here)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AppSettings` key-value model: already used for `notify_days_before` global setting — extend with `bot_token`, `chat_id`, `notify_time` keys
- `get_global_threshold(db)` in `status.py`: reuse in scheduler and notification service
- `enrich_licenses()` in `status.py`: reuse to get status-enriched license list for digest
- `License.notify_days_before`: per-license override already in schema — no migration needed

### Established Patterns
- Settings precedence: DB value → `.env` → hardcoded default — apply to all new settings keys
- Sync def routes with `db: Session = Depends(get_db)` — all new routes follow this
- HTMX partial responses: return `TemplateResponse` fragment, not JSON
- `html.escape()` on all user-provided strings before sending to Telegram

### Integration Points
- `app/main.py` lifespan: add scheduler start/stop here
- `templates/base.html` nav: add «Настройки» link pointing to `/settings`
- `app/routers/` directory: add `settings.py` router, include in `main.py`
- `app/services/` directory: add `telegram.py` and `scheduler.py`

</code_context>

<specifics>
## Specific Ideas

- Digest line format: `• VMware vCenter — 15.05.2026 (3 дня) — Иванов`
- Tier headers: `🔴 Истекло` and `🟡 Истекает скоро`
- Settings keys in `AppSettings`: `bot_token`, `chat_id`, `notify_days_before`, `notify_time`
- Scheduler reschedules on settings save when `notify_time` changes

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-notifications-settings*
*Context gathered: 2026-04-16*
