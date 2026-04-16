# Phase 4: Notifications & Settings - Research

**Researched:** 2026-04-16
**Domain:** Telegram Bot API integration, APScheduler cron jobs, HTMX settings forms
**Confidence:** HIGH

## Summary

Phase 4 closes the v1 loop by adding automated Telegram digest notifications and a Settings page. All core libraries (httpx 0.28.1, APScheduler 3.11.2) are already in `requirements.txt` and installed. The `AppSettings` key-value model and `License.notify_days_before` column already exist in the schema -- no migrations needed. The `get_global_threshold(db)` function already implements the DB-over-env precedence chain, and `enrich_licenses()` already computes per-license status with threshold override support.

The implementation breaks cleanly into four concerns: (1) a settings service/router for CRUD on `AppSettings` with an HTMX form, (2) a Telegram service wrapping `httpx.post()` to the Bot API with `html.escape()`, (3) an APScheduler `BackgroundScheduler` with `CronTrigger` started in FastAPI lifespan, and (4) wiring the test-notification endpoint and per-license threshold field into the existing edit form.

**Primary recommendation:** Use synchronous `httpx.Client` for Telegram calls (matching the sync-def-routes convention), APScheduler 3.x `BackgroundScheduler` with `CronTrigger(hour=H, minute=M)`, and mock HTTP calls in tests with `unittest.mock.patch` on `httpx.Client.post`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Licenses grouped by urgency tiers: red-circle Isteklo / yellow-circle Istekaet skoro -- two sections, emoji headers.
- **D-02:** Inclusion criteria: only licenses where `days_remaining <= global_threshold` OR expired (days <= 0). Active licenses not included.
- **D-03:** Format -- Russian plain text, `parse_mode` not required. One line per license: `* ProductName -- DD.MM.YYYY (N dney) -- Responsible`. If responsible is null, omit that field.
- **D-04:** Empty digest (0 qualifying licenses) -- send nothing. No "all clear" message.
- **D-05:** Default fire time: 09:00. Configurable via Settings UI -- stored as `notify_time` key in `AppSettings` (value format: `"HH:MM"`).
- **D-06:** Timezone: controlled by `TZ` env var in Docker Compose -- not a settings-page field.
- **D-07:** APScheduler `BackgroundScheduler` with `CronTrigger` started in FastAPI lifespan. Reschedule on settings save if time changes.
- **D-08:** Single page `GET /settings` with one form -- fields: `bot_token`, `chat_id`, `notify_days_before` (global threshold), `notify_time`.
- **D-09:** Single POST `/settings` save button. HTMX replaces form section on success/error -- no full page reload.
- **D-10:** Test notification button: `POST /settings/test-notification`. Result shown inline in `<div id="test-result">` below the button via HTMX swap.
- **D-11:** No scheduler enable/disable toggle -- scheduler runs whenever `bot_token` + `chat_id` are configured; silently skips if either is missing.
- **D-12:** Per-license threshold placement: Claude's discretion.
- **D-13:** Empty-field UX (global default): Claude's discretion.

### Claude's Discretion
- Where `notify_days_before` override field appears (add form, edit form, both)
- Placeholder/helper text when field is empty (global default fallback)
- Exact HTML structure of Settings page (field grouping, label styles)
- Error message copy for Telegram API failures (401, 400, timeout)
- Whether to show last-sent timestamp on Settings page

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| NOTF-01 | Telegram-bot sends notifications to configured chat/group | httpx sync client + Bot API sendMessage endpoint; `html.escape()` for user strings |
| NOTF-02 | Notifications sent automatically on schedule (daily) | APScheduler BackgroundScheduler + CronTrigger in lifespan |
| NOTF-03 | Notification contains: product name, expiry date, days remaining, responsible | Digest formatter using `enrich_licenses()` output, Russian format DD.MM.YYYY |
| NOTF-04 | Global notification threshold configurable via UI | Settings page form field `notify_days_before`, stored in AppSettings |
| NOTF-05 | Per-license threshold overrides global default | `License.notify_days_before` column already exists; `enrich_licenses()` already respects it |
| NOTF-06 | Telegram settings (token, chat_id) via .env or web UI | `bootstrap_settings()` already seeds from .env; Settings page edits DB values |
| SETT-01 | Settings page: Telegram token, chat_id, global threshold | `GET /settings` + `POST /settings` router with HTMX form |
| SETT-02 | Test notification button | `POST /settings/test-notification` endpoint, inline result div |
| SETT-03 | Settings persist in DB (priority over .env) | AppSettings key-value store already implements this pattern |
| LIC-06 | Per-license threshold override for global default | Add `notify_days_before` field to license edit form |
| INFRA-04 | Scheduler runs inside Python process (APScheduler) | BackgroundScheduler started/stopped in FastAPI lifespan context manager |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | 0.28.1 | Telegram Bot API HTTP calls | Already in requirements.txt; sync + async support; used by FastAPI ecosystem |
| APScheduler | 3.11.2 | In-process cron scheduling | Already in requirements.txt; BackgroundScheduler runs in same process, no Redis/Celery |
| FastAPI | 0.135.3 | Web framework | Already in use |
| SQLAlchemy | 2.0.49 | ORM for AppSettings | Already in use |
| Jinja2 | 3.1.6 | Settings page template | Already in use |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.0.2 | Test framework | Already in use for all tests |
| unittest.mock | stdlib | Mock httpx calls in tests | Use `patch` on httpx.Client.post to avoid real API calls |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| httpx sync | httpx async | Would require async routes, contradicts project convention (sync def) |
| unittest.mock | pytest-httpx 0.36.2 | pytest-httpx only works with async httpx; our routes are sync -- use stdlib mock |
| APScheduler BackgroundScheduler | AsyncIOScheduler | BackgroundScheduler is simpler with sync routes, no event loop coupling |

**Installation:**
```bash
# No new packages needed -- all already in requirements.txt
pip install -r requirements.txt
```

**Version verification:** httpx 0.28.1 (latest), APScheduler 3.11.2 (latest 3.x) -- both confirmed current via `pip index versions`.

## Architecture Patterns

### New Files
```
app/
├── services/
│   ├── telegram.py     # send_telegram_message(), format_digest()
│   └── scheduler.py    # init_scheduler(), reschedule_notification_job()
├── routers/
│   └── settings.py     # GET /settings, POST /settings, POST /settings/test-notification
templates/
├── settings.html       # Settings page (extends base.html)
├── partials/
│   └── settings_form.html  # HTMX-swappable form fragment
tests/
├── test_telegram.py    # Unit tests for Telegram service
├── test_scheduler.py   # Unit tests for scheduler
└── test_settings.py    # Integration tests for settings routes
```

### Pattern 1: Settings Service (DB-over-env Precedence)
**What:** Read/write AppSettings keys with fallback chain
**When to use:** Every settings access -- token, chat_id, threshold, notify_time
**Example:**
```python
# app/services/settings.py or inline in router
from app.models import AppSettings

def get_setting(db: Session, key: str, env_fallback: str = "") -> str:
    """DB value -> env -> empty string."""
    row = db.query(AppSettings).filter_by(key=key).first()
    if row and row.value:
        return row.value
    return env_fallback

def save_setting(db: Session, key: str, value: str):
    row = db.query(AppSettings).filter_by(key=key).first()
    if row:
        row.value = value
    else:
        db.add(AppSettings(key=key, value=value))
    db.commit()
```

### Pattern 2: Telegram Service (Sync httpx)
**What:** Send a message via Telegram Bot API using synchronous httpx
**When to use:** Digest send and test notification
**Example:**
```python
import html
import httpx

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

def send_telegram_message(token: str, chat_id: str, text: str) -> dict:
    """Send message via Telegram Bot API. Returns {"ok": True/False, "error": ...}."""
    url = TELEGRAM_API.format(token=token)
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, json={"chat_id": chat_id, "text": text})
            data = resp.json()
            if resp.status_code == 200 and data.get("ok"):
                return {"ok": True}
            # Classify error
            error_code = data.get("error_code", resp.status_code)
            description = data.get("description", "Unknown error")
            return {"ok": False, "error": description, "error_code": error_code}
    except httpx.TimeoutException:
        return {"ok": False, "error": "Timeout connecting to Telegram API", "error_code": 0}
    except httpx.HTTPError as e:
        return {"ok": False, "error": str(e), "error_code": 0}
```

### Pattern 3: APScheduler in FastAPI Lifespan
**What:** Start BackgroundScheduler on app startup, stop on shutdown
**When to use:** The daily digest cron job
**Example:**
```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = BackgroundScheduler()

def start_scheduler(hour: int = 9, minute: int = 0):
    scheduler.add_job(
        send_daily_digest,
        trigger=CronTrigger(hour=hour, minute=minute),
        id="daily_digest",
        replace_existing=True,
    )
    scheduler.start()

def reschedule_notification_job(hour: int, minute: int):
    scheduler.reschedule_job(
        "daily_digest",
        trigger=CronTrigger(hour=hour, minute=minute),
    )

# In main.py lifespan:
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_tables()
    bootstrap_settings()
    # Read notify_time from DB, parse HH:MM, start scheduler
    start_scheduler(hour=h, minute=m)
    yield
    scheduler.shutdown()
```

### Pattern 4: HTMX Settings Form
**What:** Single form with hx-post, swap form section on save
**When to use:** Settings page
**Example:**
```html
<form hx-post="/settings" hx-target="#settings-form" hx-swap="outerHTML">
  <!-- fields -->
  <button type="submit" class="btn btn-primary">Сохранить настройки</button>
</form>
<button hx-post="/settings/test-notification" hx-target="#test-result" hx-swap="innerHTML">
  Отправить тестовое уведомление
</button>
<div id="test-result"></div>
```

### Pattern 5: Digest Formatter with Urgency Grouping
**What:** Group licenses into expired / warning tiers, format Russian text
**When to use:** Building the daily digest message
**Example:**
```python
def format_digest(enriched_licenses: list, global_threshold: int) -> str | None:
    expired = [e for e in enriched_licenses if e["status"] == "expired"]
    warning = [e for e in enriched_licenses if e["status"] == "warning"]
    
    if not expired and not warning:
        return None  # D-04: send nothing
    
    lines = []
    if expired:
        lines.append("\U0001f534 Истекло")  # red circle emoji
        for e in expired:
            lines.append(format_license_line(e))
    if warning:
        lines.append("\U0001f7e1 Истекает скоро")  # yellow circle emoji
        for e in warning:
            lines.append(format_license_line(e))
    return "\n".join(lines)

def format_license_line(e: dict) -> str:
    lic = e["license"]
    date_str = lic.expiry_date.strftime("%d.%m.%Y")
    days = e["days_remaining"]
    line = f"\u2022 {html.escape(lic.product_name)} \u2014 {date_str} ({days} дн.)"
    if lic.responsible:
        line += f" \u2014 {html.escape(lic.responsible)}"
    return line
```

### Anti-Patterns to Avoid
- **Async routes for DB access:** Project convention is sync def -- do NOT use `async def` for routes that touch the database or call httpx synchronously.
- **Re-instantiating Jinja2Templates:** Use the singleton from `app/templates.py` -- never create a new instance in a router.
- **Storing secrets in code:** bot_token and chat_id go to AppSettings DB or .env, never hardcoded.
- **Sending unescaped user strings to Telegram:** Always `html.escape()` product_name and responsible before including in message text. Even though parse_mode is not set (plain text), escaping prevents injection if parse_mode is ever added.
- **Creating a separate scheduler container:** APScheduler runs in-process -- no extra docker-compose service.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cron scheduling | Custom sleep loop / threading.Timer | APScheduler BackgroundScheduler + CronTrigger | Handles missed fires, timezone, reschedule; already in requirements.txt |
| HTTP client | urllib.request / raw sockets | httpx.Client (sync) | Timeouts, JSON, connection pooling, clean error handling |
| Settings key-value store | New model / JSON file | Existing AppSettings model | Already built, tested, bootstrapped from .env |
| Status computation | Re-implement threshold logic | `enrich_licenses()` + `get_global_threshold()` | Already handles per-license override, tested |
| Time parsing | Manual string splitting | `datetime.strptime` or split on ":" | Two-field (hour, minute) is simple enough; no library needed |

## Common Pitfalls

### Pitfall 1: SQLAlchemy Session in Scheduler Thread
**What goes wrong:** APScheduler runs jobs in a thread pool. Using the FastAPI request-scoped session from a background thread causes "session is not bound" or thread-safety errors.
**Why it happens:** `get_session()` yields a request-scoped session via Depends. The scheduler job runs outside the request lifecycle.
**How to avoid:** Create a fresh session in the scheduler job function using `Session(engine)` directly, not via `get_session()` or Depends.
**Warning signs:** Random "OperationalError: database is locked" or "DetachedInstanceError" in logs.

### Pitfall 2: Scheduler Double-Start on Reload
**What goes wrong:** With uvicorn `--reload`, the lifespan runs again, starting a second scheduler instance.
**Why it happens:** APScheduler's BackgroundScheduler is a module-level singleton; if `start()` is called twice, it raises `SchedulerAlreadyRunningError`.
**How to avoid:** Guard with `if not scheduler.running: scheduler.start()` or use `replace_existing=True` when adding jobs.
**Warning signs:** `SchedulerAlreadyRunningError` on reload.

### Pitfall 3: Bot Token in Telegram URL
**What goes wrong:** Logging the full Telegram API URL exposes the bot token in logs.
**Why it happens:** Token is part of the URL path: `https://api.telegram.org/bot<TOKEN>/sendMessage`.
**How to avoid:** Never log the full URL. Log only status codes and error descriptions.
**Warning signs:** Token visible in docker-compose logs.

### Pitfall 4: Empty bot_token / chat_id Crashes Scheduler
**What goes wrong:** The scheduler job fires but token/chat_id are empty strings, causing a 404 or 401 from Telegram API.
**Why it happens:** App starts before user configures settings.
**How to avoid:** Check `if not token or not chat_id: return` at the top of the digest job. This is locked decision D-11.
**Warning signs:** Repeated error logs every day at 09:00.

### Pitfall 5: Timezone Mismatch
**What goes wrong:** Scheduler fires at wrong local time.
**Why it happens:** Container default timezone is UTC; team expects local time.
**How to avoid:** Set `TZ` env var in `docker-compose.yml` (decision D-06). APScheduler's CronTrigger uses the system timezone by default.
**Warning signs:** Digest arrives at unexpected hour.

### Pitfall 6: HTMX Swap Target Mismatch
**What goes wrong:** Settings form HTMX response replaces wrong element or shows raw HTML.
**Why it happens:** `hx-target` ID doesn't match the returned fragment's wrapper ID.
**How to avoid:** Return the exact same wrapper element (same ID) in both the initial GET and the POST response. Use `hx-swap="outerHTML"` consistently.
**Warning signs:** Form duplicates or disappears after save.

## Code Examples

### Telegram Bot API sendMessage (verified from official docs)
```python
# Telegram Bot API endpoint
# POST https://api.telegram.org/bot{token}/sendMessage
# Body (JSON): {"chat_id": "...", "text": "..."}
# Response: {"ok": true, "result": {...}} or {"ok": false, "error_code": 401, "description": "Unauthorized"}
#
# Common error codes:
#   401 - Invalid bot token ("Unauthorized")
#   400 - Bad request (missing chat_id, empty text, malformed request)
#   403 - Bot was blocked by user or bot is not a member of the chat
#   429 - Too many requests (rate limited, includes retry_after field)

import httpx
import html

def send_telegram_message(token: str, chat_id: str, text: str) -> dict:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, json=payload)
        data = resp.json()
        if data.get("ok"):
            return {"ok": True}
        return {
            "ok": False,
            "error": data.get("description", "Unknown error"),
            "error_code": data.get("error_code", resp.status_code),
        }
    except httpx.TimeoutException:
        return {"ok": False, "error": "Тайм-аут соединения с Telegram", "error_code": 0}
    except httpx.HTTPError as exc:
        return {"ok": False, "error": f"Ошибка HTTP: {exc}", "error_code": 0}
```

### APScheduler Reschedule Pattern
```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = BackgroundScheduler()

def init_scheduler(hour: int, minute: int):
    """Start scheduler with daily digest job."""
    scheduler.add_job(
        send_daily_digest,
        trigger=CronTrigger(hour=hour, minute=minute),
        id="daily_digest",
        replace_existing=True,
        misfire_grace_time=3600,  # allow 1 hour late fire
    )
    if not scheduler.running:
        scheduler.start()

def reschedule_digest(hour: int, minute: int):
    """Update fire time without restarting scheduler."""
    scheduler.reschedule_job(
        "daily_digest",
        trigger=CronTrigger(hour=hour, minute=minute),
    )
```

### Scheduler Job with Own Session
```python
from sqlalchemy.orm import Session
from app.database import engine
from app.models import License, AppSettings
from app.services.status import enrich_licenses, get_global_threshold
from app.services.telegram import send_telegram_message, format_digest

def send_daily_digest():
    """Scheduled job -- runs in APScheduler thread, creates own DB session."""
    with Session(engine) as db:
        token = _get_setting(db, "telegram_bot_token")
        chat_id = _get_setting(db, "telegram_chat_id")
        if not token or not chat_id:
            return  # D-11: silently skip

        threshold = get_global_threshold(db)
        licenses = db.query(License).all()
        enriched = enrich_licenses(licenses, threshold)

        message = format_digest(enriched, threshold)
        if message is None:
            return  # D-04: nothing to send

        send_telegram_message(token, chat_id, message)
```

### Test with Mocked httpx
```python
from unittest.mock import patch, MagicMock

def test_send_telegram_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"ok": True, "result": {}}

    with patch("httpx.Client") as MockClient:
        MockClient.return_value.__enter__ = lambda s: s
        MockClient.return_value.__exit__ = MagicMock(return_value=False)
        MockClient.return_value.post.return_value = mock_response

        result = send_telegram_message("token", "chat_id", "test")
        assert result["ok"] is True
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| APScheduler 4.x (alpha) | APScheduler 3.11.2 (stable) | 3.x is stable, 4.x still alpha | Stick with 3.x -- project already depends on it |
| requests library | httpx 0.28.1 | httpx is the modern choice | Already in requirements.txt; sync + async capable |
| Celery + Redis | APScheduler in-process | Project decision | No extra infrastructure needed |

## Open Questions

1. **Per-license threshold field placement**
   - What we know: `License.notify_days_before` column exists. It's Claude's discretion (D-12).
   - Recommendation: Add to BOTH add and edit forms. On add form, it's optional with placeholder text showing global default. On edit form, show current value or empty for global default.

2. **Last-sent timestamp display**
   - What we know: Claude's discretion per CONTEXT.md.
   - Recommendation: Store `last_digest_sent` in AppSettings after successful digest send. Show on Settings page as informational text -- low effort, high value for operators.

3. **Error message copy for Telegram failures**
   - What we know: Claude's discretion per CONTEXT.md.
   - Recommendation: Russian error messages mapped from API error codes:
     - 401: "Неверный токен бота"
     - 400: "Некорректный запрос (проверьте chat_id)"
     - 403: "Бот заблокирован или не добавлен в чат"
     - 429: "Слишком много запросов, попробуйте позже"
     - Timeout: "Тайм-аут соединения с Telegram"

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | None (default discovery) |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| NOTF-01 | send_telegram_message() calls Bot API correctly | unit | `pytest tests/test_telegram.py::test_send_telegram_success -x` | Wave 0 |
| NOTF-01 | Error classification (401, 400, 403, timeout) | unit | `pytest tests/test_telegram.py::test_send_telegram_error_codes -x` | Wave 0 |
| NOTF-02 | Scheduler starts in lifespan, fires daily | unit | `pytest tests/test_scheduler.py::test_scheduler_starts -x` | Wave 0 |
| NOTF-03 | Digest contains product, date, days, responsible | unit | `pytest tests/test_telegram.py::test_format_digest -x` | Wave 0 |
| NOTF-04 | Settings page saves global threshold | integration | `pytest tests/test_settings.py::test_save_threshold -x` | Wave 0 |
| NOTF-05 | Per-license override respected in digest | unit | `pytest tests/test_telegram.py::test_digest_per_license_threshold -x` | Wave 0 |
| NOTF-06 | Token/chat_id saved via settings page | integration | `pytest tests/test_settings.py::test_save_telegram_credentials -x` | Wave 0 |
| SETT-01 | GET /settings renders form with current values | integration | `pytest tests/test_settings.py::test_settings_page_renders -x` | Wave 0 |
| SETT-02 | POST /settings/test-notification sends test msg | integration | `pytest tests/test_settings.py::test_notification_endpoint -x` | Wave 0 |
| SETT-03 | Settings persist in DB, survive restart | integration | `pytest tests/test_settings.py::test_settings_persist -x` | Wave 0 |
| LIC-06 | notify_days_before field on edit form, saved to DB | integration | `pytest tests/test_settings.py::test_per_license_threshold_form -x` | Wave 0 |
| INFRA-04 | APScheduler BackgroundScheduler in lifespan | unit | `pytest tests/test_scheduler.py::test_scheduler_in_lifespan -x` | Wave 0 |
| D-04 | Empty digest sends nothing | unit | `pytest tests/test_telegram.py::test_empty_digest_returns_none -x` | Wave 0 |
| D-07 | Reschedule on settings save | unit | `pytest tests/test_scheduler.py::test_reschedule -x` | Wave 0 |
| D-11 | Skip if token/chat_id missing | unit | `pytest tests/test_scheduler.py::test_skip_when_unconfigured -x` | Wave 0 |
| REGR | All existing tests still pass | regression | `pytest tests/ -v` | Existing |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_telegram.py` -- covers NOTF-01, NOTF-03, NOTF-05, D-04
- [ ] `tests/test_scheduler.py` -- covers NOTF-02, INFRA-04, D-07, D-11
- [ ] `tests/test_settings.py` -- covers SETT-01, SETT-02, SETT-03, NOTF-04, NOTF-06, LIC-06

### Manual Verification Required
| Item | Why Manual | How to Verify |
|------|-----------|---------------|
| Telegram message actually arrives in chat | Requires real bot token + chat | Configure real credentials, click "Test notification", check Telegram app |
| Scheduler fires at correct local time | Requires running container with TZ set | Set TZ, wait for fire time, check logs |
| Settings page renders correctly (visual) | CSS/layout verification | Open `/settings` in browser |
| HTMX inline swap on save/test | Dynamic UI behavior | Click save, observe no page reload, check form updates |

## Sources

### Primary (HIGH confidence)
- `requirements.txt` -- httpx 0.28.1, APScheduler 3.11.2 already listed
- `app/models.py` -- AppSettings and License.notify_days_before schema verified
- `app/services/status.py` -- get_global_threshold() and enrich_licenses() code reviewed
- `app/database.py` -- bootstrap_settings() seeds telegram keys from .env
- `app/config.py` -- TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, NOTIFY_DAYS_BEFORE env vars

### Secondary (MEDIUM confidence)
- [Telegram Bot API docs](https://core.telegram.org/bots/api) -- sendMessage parameters, error codes
- [APScheduler 3.x user guide](https://apscheduler.readthedocs.io/en/3.x/userguide.html) -- BackgroundScheduler, CronTrigger, reschedule_job
- [APScheduler CronTrigger docs](https://apscheduler.readthedocs.io/en/3.x/modules/triggers/cron.html) -- hour/minute parameters
- [httpx quickstart](https://www.python-httpx.org/quickstart/) -- sync Client usage, timeout, JSON posting

### Tertiary (LOW confidence)
- None -- all critical claims verified against codebase and official docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in requirements.txt, versions verified
- Architecture: HIGH -- patterns follow established project conventions (sync routes, HTMX partials, AppSettings model)
- Pitfalls: HIGH -- based on direct code analysis (session threading, scheduler lifecycle) and known Telegram API behavior

**Research date:** 2026-04-16
**Valid until:** 2026-05-16 (stable stack, no fast-moving dependencies)
