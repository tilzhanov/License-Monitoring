# Telegram Notification Integration Research

**Project:** License Monitoring Dashboard
**Researched:** 2026-04-03
**Overall confidence:** MEDIUM-HIGH (based on training data; external docs unavailable during research session)

---

## 1. python-telegram-bot vs httpx Direct Calls

### Recommendation: httpx direct calls

For a one-way notification sender (no commands, no polling, no interaction), `python-telegram-bot` is overengineered. The library is built around the `Application` runner loop and update polling — exactly what you don't need. Using it correctly in FastAPI requires fighting its own async lifecycle.

**httpx wins for this use case because:**

- No bot runner lifecycle to manage alongside FastAPI's lifespan
- No dependency on a 1,200+ line library when you only call one endpoint
- Full async/await compatibility with FastAPI's event loop out of the box
- Explicit control — you own the HTTP client, the session, the error handling
- Simpler testing — mock a single `httpx.AsyncClient` rather than mocking PTB internals

**When python-telegram-bot is the right choice:**
- You need to receive updates (commands, inline buttons, user replies)
- You're building a bot with conversation handlers
- Neither applies to this project

**httpx integration pattern for FastAPI:**

```python
# services/telegram.py
import httpx
from typing import Optional

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}"


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=10.0)
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    def _url(self, method: str) -> str:
        return f"https://api.telegram.org/bot{self.bot_token}/{method}"

    async def send_message(self, text: str, parse_mode: str = "HTML") -> dict:
        if self._client is None:
            raise RuntimeError("TelegramNotifier must be used as async context manager")
        response = await self._client.post(
            self._url("sendMessage"),
            json={
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode,
            },
        )
        response.raise_for_status()
        return response.json()
```

**FastAPI lifespan integration — share a single client:**

```python
# main.py
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Shared HTTP client for the app lifetime
    app.state.http_client = httpx.AsyncClient(timeout=10.0)
    yield
    await app.state.http_client.aclose()

app = FastAPI(lifespan=lifespan)
```

**Alternative: thin standalone function (simpler for single use case):**

```python
# services/telegram.py
import httpx

async def send_telegram_message(
    bot_token: str,
    chat_id: str,
    text: str,
    parse_mode: str = "HTML",
) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            url,
            json={"chat_id": chat_id, "text": text, "parse_mode": parse_mode},
        )
        response.raise_for_status()
```

The standalone function creates/closes a client per call. Acceptable for low-frequency daily scheduler use; use the shared-client pattern if you need the test-message endpoint to respond fast.

**Confidence:** HIGH — httpx is the de facto async HTTP client for FastAPI projects; python-telegram-bot's own docs state v20+ requires its Application runner which conflicts with external event loops.

---

## 2. Message Formatting

### Recommendation: HTML parse mode

**MarkdownV2 problems:**
- Requires escaping 18+ characters: `_ * [ ] ( ) ~ ` > # + - = | { } . !`
- License names and product names (e.g., `vCloud Director`, `Veeam B&R`) frequently contain characters that must be escaped
- A single unescaped character silently breaks the entire message — Telegram returns an error, message is not delivered
- Escaping logic is error-prone and hard to test

**HTML advantages:**
- Only `<`, `>`, `&` need escaping (standard HTML entity encoding)
- Python's `html.escape()` handles this correctly
- Tags are explicit: `<b>`, `<i>`, `<code>`, `<a href="...">`
- Easier to read in code, easier to unit test

**Supported HTML tags in Telegram:**

| Tag | Effect | Use for |
|-----|--------|---------|
| `<b>bold</b>` | Bold | Product names, status labels |
| `<i>italic</i>` | Italic | Secondary info |
| `<code>text</code>` | Monospace | Dates, IDs |
| `<u>underline</u>` | Underline | (rarely needed) |
| `<a href="url">text</a>` | Hyperlink | Link to dashboard |

**License expiry notification template:**

```python
import html
from datetime import date

def format_expiry_alert(
    product: str,
    expires_on: date,
    days_remaining: int,
    responsible: str,
    dashboard_url: str = "",
) -> str:
    product_safe = html.escape(product)
    responsible_safe = html.escape(responsible)
    date_str = expires_on.strftime("%d.%m.%Y")

    if days_remaining < 0:
        status_line = f"🔴 <b>ИСТЕКЛА</b> {abs(days_remaining)} дн. назад"
    elif days_remaining == 0:
        status_line = "🔴 <b>ИСТЕКАЕТ СЕГОДНЯ</b>"
    elif days_remaining <= 7:
        status_line = f"🔴 <b>Критично</b> — {days_remaining} дн."
    elif days_remaining <= 30:
        status_line = f"🟡 <b>Скоро</b> — {days_remaining} дн."
    else:
        status_line = f"🟢 <b>Предупреждение</b> — {days_remaining} дн."

    lines = [
        "⚠️ <b>Уведомление об истечении лицензии</b>",
        "",
        f"📦 <b>Продукт:</b> {product_safe}",
        f"📅 <b>Дата истечения:</b> <code>{date_str}</code>",
        f"{status_line}",
        f"👤 <b>Ответственный:</b> {responsible_safe}",
    ]

    if dashboard_url:
        lines.append(f"\n<a href=\"{dashboard_url}\">Открыть дашборд</a>")

    return "\n".join(lines)
```

**Batch notification pattern (multiple licenses in one message):**

When multiple licenses are expiring soon, send one summary message instead of N individual messages (avoids Telegram rate limits and notification spam):

```python
def format_daily_digest(licenses: list[dict], dashboard_url: str = "") -> str:
    lines = ["⚠️ <b>Отчёт об истекающих лицензиях</b>", ""]

    critical = [l for l in licenses if l["days_remaining"] <= 7]
    warning  = [l for l in licenses if 7 < l["days_remaining"] <= 30]
    notice   = [l for l in licenses if l["days_remaining"] > 30]

    def render_group(title: str, items: list[dict]) -> list[str]:
        result = [f"<b>{title}</b>"]
        for lic in items:
            product = html.escape(lic["product"])
            date_str = lic["expires_on"].strftime("%d.%m.%Y")
            days = lic["days_remaining"]
            result.append(f"  • {product} — <code>{date_str}</code> ({days} дн.)")
        return result

    if critical:
        lines += render_group("🔴 Критично (≤7 дней)", critical) + [""]
    if warning:
        lines += render_group("🟡 Скоро (≤30 дней)", warning) + [""]
    if notice:
        lines += render_group("🟢 Предупреждение", notice) + [""]

    lines.append(f"Всего лицензий под контролем: {len(licenses)}")

    if dashboard_url:
        lines.append(f"\n<a href=\"{dashboard_url}\">Открыть дашборд</a>")

    return "\n".join(lines)
```

**Message length:** Telegram's max is 4096 characters per message. A digest of 50 licenses will stay well under that. For very large lists, split at 50 items per message.

**Confidence:** HIGH — Telegram Bot API HTML parse mode is stable, well-documented, and the escaping requirements are unchanged.

---

## 3. APScheduler + Telegram Integration

### Recommendation: APScheduler with AsyncScheduler (v4) or BackgroundScheduler (v3)

**APScheduler version considerations:**

- **APScheduler v3.x** — Mature, widely used, uses `BackgroundScheduler` which runs in a thread. Works with FastAPI but requires `run_coroutine_threadsafe` or wrapping async calls.
- **APScheduler v4.x** — Native async support with `AsyncScheduler`. Cleaner integration with FastAPI's async context. Still relatively new (released 2024).

**Recommendation: APScheduler v3 with ThreadPoolExecutor** for stability, or **v4 AsyncScheduler** if you want cleaner async code. The v3 pattern is more battle-tested.

**APScheduler v3 pattern (stable, recommended for production):**

```python
# scheduler.py
import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


def create_scheduler(app) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        daily_notification_check,
        trigger=CronTrigger(hour=9, minute=0),  # 09:00 every day
        id="daily_license_check",
        replace_existing=True,
        kwargs={"app": app},
    )
    return scheduler


async def daily_notification_check(app) -> None:
    """Query expiring licenses and send Telegram notification."""
    from services.settings import get_effective_settings
    from services.licenses import get_expiring_licenses
    from services.telegram import send_telegram_message
    from services.formatting import format_daily_digest

    logger.info("Running daily license notification check")

    try:
        settings = await get_effective_settings(app.state.db)
        if not settings.telegram_token or not settings.telegram_chat_id:
            logger.warning("Telegram not configured, skipping notification")
            return

        licenses = await get_expiring_licenses(
            app.state.db,
            threshold_days=settings.notification_threshold_days,
        )

        if not licenses:
            logger.info("No licenses expiring soon, no notification sent")
            return

        message = format_daily_digest(licenses, settings.dashboard_url)
        await send_telegram_message(
            bot_token=settings.telegram_token,
            chat_id=settings.telegram_chat_id,
            text=message,
        )
        logger.info(f"Notification sent for {len(licenses)} license(s)")

    except TelegramAPIError as e:
        logger.error(f"Telegram API error during daily check: {e}")
        # Do not re-raise — scheduler must not crash on API failure
    except Exception as e:
        logger.error(f"Unexpected error in daily notification check: {e}", exc_info=True)
```

**FastAPI lifespan integration:**

```python
# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from scheduler import create_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = create_scheduler(app)
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)

app = FastAPI(lifespan=lifespan)
```

**Error handling strategy for Telegram API unavailability:**

| Error Type | Action | Rationale |
|------------|--------|-----------|
| `httpx.TimeoutException` | Log warning, return | Transient; retry next day is acceptable |
| `httpx.HTTPStatusError` (4xx) | Log error with status code; alert via stderr | Bad config (wrong token/chat_id); won't self-heal |
| `httpx.HTTPStatusError` (5xx) | Log warning, return | Telegram server error; retry next scheduled run |
| `httpx.ConnectError` | Log warning, return | Network partition; retry next run |
| Any unhandled exception | Log critical, return (never raise) | Scheduler must not die |

```python
# services/telegram.py
import httpx
import logging

logger = logging.getLogger(__name__)


class TelegramAPIError(Exception):
    """Raised when Telegram returns a non-2xx response."""
    def __init__(self, status_code: int, description: str):
        self.status_code = status_code
        self.description = description
        super().__init__(f"Telegram API error {status_code}: {description}")


async def send_telegram_message(
    bot_token: str,
    chat_id: str,
    text: str,
    parse_mode: str = "HTML",
) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                json={"chat_id": chat_id, "text": text, "parse_mode": parse_mode},
            )
        if not response.is_success:
            data = response.json()
            description = data.get("description", "unknown error")
            raise TelegramAPIError(response.status_code, description)

    except httpx.TimeoutException:
        logger.warning("Telegram API request timed out")
        raise
    except httpx.ConnectError:
        logger.warning("Cannot connect to Telegram API (network issue)")
        raise
    except TelegramAPIError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error sending Telegram message: {e}")
        raise
```

**Cron time zone handling:** APScheduler defaults to UTC. For a team in Kazakhstan (UTC+5 or UTC+6 depending on season), set the timezone explicitly:

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz

scheduler = AsyncIOScheduler(timezone=pytz.timezone("Asia/Almaty"))
```

Or use `Asia/Bishkek` (UTC+6, no DST). Check the server's local timezone to avoid double-confusion.

**Confidence:** HIGH for APScheduler v3 AsyncIOScheduler pattern; MEDIUM for v4 (newer, less battle-tested).

---

## 4. Configuration Management

### Recommendation: DB overrides .env, with explicit fallback chain

The pattern where DB settings take precedence over .env lets operators bootstrap the system via Docker env vars but then manage settings through the UI without restarting containers.

**Precedence order (highest to lowest):**
1. Database settings table (user-configured via settings page)
2. Environment variables / .env file (bootstrap defaults)
3. Application defaults (hardcoded fallbacks)

**Settings model (SQLAlchemy):**

```python
# models/settings.py
from sqlalchemy import Column, String, Integer
from database import Base

class AppSettings(Base):
    __tablename__ = "app_settings"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=True)

# Keys used:
# "telegram_bot_token"
# "telegram_chat_id"
# "notification_threshold_days"
# "dashboard_url"
```

**Settings service with fallback chain:**

```python
# services/settings.py
import os
from dataclasses import dataclass
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from models.settings import AppSettings

DEFAULTS = {
    "notification_threshold_days": "30",
    "dashboard_url": "",
}


@dataclass
class EffectiveSettings:
    telegram_token: Optional[str]
    telegram_chat_id: Optional[str]
    notification_threshold_days: int
    dashboard_url: str

    @property
    def is_telegram_configured(self) -> bool:
        return bool(self.telegram_token and self.telegram_chat_id)


async def get_db_setting(db: AsyncSession, key: str) -> Optional[str]:
    result = await db.get(AppSettings, key)
    return result.value if result else None


async def get_effective_settings(db: AsyncSession) -> EffectiveSettings:
    """
    Resolve settings using DB-over-env precedence.
    DB values take priority; env vars are the fallback.
    """
    async def resolve(key: str, env_var: str) -> Optional[str]:
        db_val = await get_db_setting(db, key)
        if db_val is not None:
            return db_val
        return os.getenv(env_var) or DEFAULTS.get(key)

    token = await resolve("telegram_bot_token", "TELEGRAM_BOT_TOKEN")
    chat_id = await resolve("telegram_chat_id", "TELEGRAM_CHAT_ID")
    threshold_raw = await resolve("notification_threshold_days", "NOTIFICATION_THRESHOLD_DAYS")
    dashboard_url = await resolve("dashboard_url", "DASHBOARD_URL")

    return EffectiveSettings(
        telegram_token=token or None,
        telegram_chat_id=chat_id or None,
        notification_threshold_days=int(threshold_raw or 30),
        dashboard_url=dashboard_url or "",
    )


async def save_setting(db: AsyncSession, key: str, value: str) -> None:
    existing = await db.get(AppSettings, key)
    if existing:
        existing.value = value
    else:
        db.add(AppSettings(key=key, value=value))
    await db.commit()
```

**.env file structure:**

```dotenv
# Telegram Bot (can be overridden via settings page)
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
TELEGRAM_CHAT_ID=-1001234567890

# Notification defaults
NOTIFICATION_THRESHOLD_DAYS=30
DASHBOARD_URL=http://192.168.1.100:8000

# App
APP_PORT=8000
DATABASE_PATH=/data/licenses.db
```

**Security note for tokens:** Never log `telegram_token` values. When displaying settings in the UI, mask the token: show only the first 10 characters + `...`. Store tokens as plain text in SQLite — the database file is protected by filesystem permissions, which is acceptable for an internal tool. For a higher-security environment, consider encrypting at rest with Fernet (but this adds complexity).

**Settings page API endpoints:**

```python
# api/settings.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/settings")


class TelegramSettingsUpdate(BaseModel):
    bot_token: str
    chat_id: str
    threshold_days: int = 30


@router.put("/telegram")
async def update_telegram_settings(
    data: TelegramSettingsUpdate,
    db: AsyncSession = Depends(get_db),
):
    await save_setting(db, "telegram_bot_token", data.bot_token)
    await save_setting(db, "telegram_chat_id", data.chat_id)
    await save_setting(db, "notification_threshold_days", str(data.threshold_days))
    return {"status": "saved"}
```

**Confidence:** HIGH — this is a standard pattern for settings with env-var bootstrapping and DB override, used widely in self-hosted tools.

---

## 5. Testing Notifications

### Recommendation: Dedicated endpoint that sends a real message synchronously

The "send test message" feature should:
1. Read current effective settings (DB + env fallback)
2. Immediately attempt to send a real Telegram message
3. Return success or a descriptive error to the UI
4. Not touch the scheduler — it's a one-shot call

**Test message endpoint:**

```python
# api/settings.py (continued)
from services.telegram import send_telegram_message, TelegramAPIError
from services.settings import get_effective_settings
import httpx

@router.post("/telegram/test")
async def test_telegram_notification(
    db: AsyncSession = Depends(get_db),
):
    settings = await get_effective_settings(db)

    if not settings.is_telegram_configured:
        raise HTTPException(
            status_code=400,
            detail="Telegram not configured. Set bot token and chat ID first.",
        )

    test_message = (
        "✅ <b>Тестовое уведомление</b>\n\n"
        "License Monitoring Dashboard настроен корректно.\n"
        "Уведомления об истечении лицензий будут приходить в этот чат."
    )

    try:
        await send_telegram_message(
            bot_token=settings.telegram_token,
            chat_id=settings.telegram_chat_id,
            text=test_message,
        )
        return {"status": "sent", "message": "Test notification delivered successfully"}

    except TelegramAPIError as e:
        # Translate Telegram error codes to user-friendly messages
        if e.status_code == 401:
            detail = "Invalid bot token. Check your TELEGRAM_BOT_TOKEN."
        elif e.status_code == 400 and "chat not found" in e.description.lower():
            detail = "Chat not found. Check your TELEGRAM_CHAT_ID and ensure the bot is added to the chat."
        elif e.status_code == 403:
            detail = "Bot was blocked or kicked from the chat. Re-add the bot and try again."
        else:
            detail = f"Telegram API error: {e.description}"
        raise HTTPException(status_code=502, detail=detail)

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Telegram API request timed out. Check network connectivity.",
        )

    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Cannot reach Telegram API. Check network/firewall settings.",
        )
```

**HTMX integration for the test button (settings page):**

```html
<button
    hx-post="/api/settings/telegram/test"
    hx-target="#test-result"
    hx-swap="innerHTML"
    hx-indicator="#test-spinner"
    class="btn btn-secondary">
    Отправить тестовое уведомление
</button>

<span id="test-spinner" class="htmx-indicator">Отправка...</span>
<div id="test-result"></div>
```

Return a small HTML fragment from the endpoint (or use a separate Jinja2 route that returns HTML). For the JSON API approach, use HTMX's `hx-on` to display results.

**Common Telegram error codes and their meaning:**

| HTTP Status | Telegram Error | Cause |
|-------------|----------------|-------|
| 401 | Unauthorized | Invalid bot token |
| 400 | Bad Request: chat not found | Wrong chat_id or bot not in chat |
| 400 | Bad Request: can't parse entities | Message formatting error (unescaped HTML) |
| 403 | Forbidden: bot was kicked | Bot removed from group |
| 403 | Forbidden: bot can't send messages | Bot blocked by user (DM) |
| 429 | Too Many Requests | Rate limited; check `retry_after` in response |

**Unit testing the notification service (without hitting Telegram API):**

```python
# tests/test_telegram.py
import pytest
import httpx
import respx  # pip install respx — httpx mock library

from services.telegram import send_telegram_message, TelegramAPIError

@respx.mock
@pytest.mark.asyncio
async def test_send_message_success():
    respx.post("https://api.telegram.org/bot123:ABC/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {}})
    )
    # Should not raise
    await send_telegram_message("123:ABC", "-100123", "Test message")


@respx.mock
@pytest.mark.asyncio
async def test_send_message_invalid_token():
    respx.post("https://api.telegram.org/botBAD_TOKEN/sendMessage").mock(
        return_value=httpx.Response(
            401, json={"ok": False, "error_code": 401, "description": "Unauthorized"}
        )
    )
    with pytest.raises(TelegramAPIError) as exc_info:
        await send_telegram_message("BAD_TOKEN", "-100123", "Test")
    assert exc_info.value.status_code == 401


@respx.mock
@pytest.mark.asyncio
async def test_send_message_timeout():
    respx.post("https://api.telegram.org/bot123:ABC/sendMessage").mock(
        side_effect=httpx.TimeoutException("timed out")
    )
    with pytest.raises(httpx.TimeoutException):
        await send_telegram_message("123:ABC", "-100123", "Test")
```

`respx` is the standard httpx mocking library — it integrates cleanly and requires no monkey-patching.

**Confidence:** HIGH — the endpoint pattern is straightforward; Telegram error code mapping is well-documented.

---

## Summary: Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| HTTP client | `httpx` (direct) | No need for python-telegram-bot's update handling overhead |
| Message format | HTML parse mode | Safe escaping via `html.escape()`, fewer edge cases than MarkdownV2 |
| Scheduler | APScheduler `AsyncIOScheduler` | Native async, no thread-pool workarounds, integrates with FastAPI lifespan |
| Config precedence | DB overrides env | Enables runtime reconfiguration without container restarts |
| Test notification | Real API call, sync endpoint | Validates full path; immediate user feedback with error translation |
| Error handling | Log + return (never crash scheduler) | Daily check must survive Telegram outages |

## Dependencies to Add

```toml
# pyproject.toml / requirements.txt
httpx>=0.27.0          # Async HTTP client
apscheduler>=3.10.0    # Job scheduler (v3, stable)
pytz>=2024.1           # Timezone support for scheduler

# Dev / testing
respx>=0.21.0          # httpx request mocking
pytest-asyncio>=0.23.0 # Async test support
```

## Pitfalls to Avoid

1. **Using `requests` instead of `httpx`** — `requests` is synchronous; calling it from an async FastAPI handler blocks the event loop. Always use `httpx.AsyncClient`.

2. **Creating a new `httpx.AsyncClient` per request in high-traffic paths** — for the scheduler (one call/day) this is fine. For the test endpoint (user-triggered) it's also fine. Don't share one client across the scheduler and web handlers without proper lifecycle management.

3. **Unescaped HTML in message text** — always pass user-provided strings through `html.escape()` before inserting into HTML-formatted messages. Product names like `VMware vCenter & vCloud` contain `&` which must become `&amp;`.

4. **Hardcoding UTC for the scheduler cron** — the scheduler timezone must match the team's working timezone or the 09:00 notification arrives at 04:00 local time.

5. **Sending one message per license** — Telegram enforces rate limits (30 messages/second to different chats, 1 message/second to the same chat). Always batch daily checks into a single digest message.

6. **Storing raw token in logs** — mask tokens in all logging statements: `token[:10] + "..."`.

7. **Not handling the case where Telegram is misconfigured** — if `telegram_token` or `telegram_chat_id` is empty, the scheduler job must return early with a warning log, not crash.

---

*Confidence note: External docs (Telegram API, python-telegram-bot, httpx, APScheduler) were inaccessible during this research session (WebFetch/WebSearch denied). Findings are based on training data through August 2025. The Telegram Bot API is stable and these patterns are consistent across versions. Verify httpx and APScheduler version compatibility with the final `requirements.txt` before implementation.*
