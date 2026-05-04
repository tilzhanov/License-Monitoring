import logging
import re

from apscheduler.jobstores.base import JobLookupError
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.config import NOTIFY_DAYS_BEFORE, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from app.database import SessionDep
from app.models import AppSettings
from app.templates import templates
from app.services.scheduler import reschedule_digest
from app.services.telegram import send_telegram_message

logger = logging.getLogger(__name__)

router = APIRouter(tags=["settings"])


def get_setting(db: Session, key: str, env_fallback: str = "") -> str:
    """Query AppSettings by key; return row.value if found and non-empty, else env_fallback."""
    row = db.query(AppSettings).filter(AppSettings.key == key).first()
    if row is not None and row.value:
        return row.value
    return env_fallback


def save_setting(db: Session, key: str, value: str) -> None:
    """Upsert an AppSettings row for the given key."""
    row = db.query(AppSettings).filter(AppSettings.key == key).first()
    if row is not None:
        row.value = value
    else:
        db.add(AppSettings(key=key, value=value))
    db.commit()


def _telegram_status() -> dict:
    """Return read-only Telegram credential status from .env (never DB)."""
    token_set = bool(TELEGRAM_BOT_TOKEN)
    chat_set = bool(TELEGRAM_CHAT_ID)
    return {
        "token_configured": token_set,
        "chat_configured": chat_set,
        "token_masked": (TELEGRAM_BOT_TOKEN[:4] + "…" + TELEGRAM_BOT_TOKEN[-4:]) if token_set and len(TELEGRAM_BOT_TOKEN) >= 8 else "",
        "chat_masked": TELEGRAM_CHAT_ID if chat_set else "",
    }


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, db: SessionDep):
    """Render settings page. Telegram secrets read-only from .env; thresholds from DB."""
    notify_days_before = get_setting(db, "notify_days_before", str(NOTIFY_DAYS_BEFORE))
    notify_time = get_setting(db, "notify_time", "09:00")

    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            "notify_days_before": notify_days_before,
            "notify_time": notify_time,
            "telegram": _telegram_status(),
            "errors": {},
            "success": False,
            "success_message": "",
        },
    )


@router.post("/settings", response_class=HTMLResponse)
def save_settings(
    request: Request,
    db: SessionDep,
    notify_days_before: str = Form("60"),
    notify_time: str = Form("09:00"),
):
    """Save non-secret settings; return HTMX-swappable form fragment."""
    errors: dict[str, str] = {}

    try:
        days_val = int(notify_days_before)
        if days_val <= 0:
            raise ValueError
    except (ValueError, TypeError):
        errors["notify_days_before"] = "Укажите положительное целое число"

    time_match = re.match(r"^(\d{2}):(\d{2})$", notify_time)
    if not time_match:
        errors["notify_time"] = "Укажите время в формате ЧЧ:ММ"
    else:
        hour, minute = int(time_match.group(1)), int(time_match.group(2))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            errors["notify_time"] = "Укажите корректное время (00:00–23:59)"

    if errors:
        return templates.TemplateResponse(
            request=request,
            name="partials/settings_form.html",
            context={
                "notify_days_before": notify_days_before,
                "notify_time": notify_time,
                "telegram": _telegram_status(),
                "errors": errors,
                "success": False,
                "success_message": "",
            },
        )

    save_setting(db, "notify_days_before", notify_days_before)
    save_setting(db, "notify_time", notify_time)

    h, m = int(notify_time.split(":")[0]), int(notify_time.split(":")[1])
    try:
        reschedule_digest(h, m)
    except JobLookupError:
        # Scheduler running but job not registered (e.g. test env) — safe to ignore.
        logger.debug("daily_digest job not registered; skipping reschedule")

    return templates.TemplateResponse(
        request=request,
        name="partials/settings_form.html",
        context={
            "notify_days_before": notify_days_before,
            "notify_time": notify_time,
            "telegram": _telegram_status(),
            "errors": {},
            "success": True,
            "success_message": "Настройки сохранены",
        },
    )


@router.post("/settings/test-notification", response_class=HTMLResponse)
def test_notification():
    """Send a test Telegram message using credentials from .env. Returns inline HTML."""
    token = TELEGRAM_BOT_TOKEN
    chat_id = TELEGRAM_CHAT_ID

    if not token or not chat_id:
        return HTMLResponse(
            content='<div class="alert alert-error">Сначала настройте TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID в .env</div>'
        )

    result = send_telegram_message(token, chat_id, "License Monitor: тестовое уведомление отправлено успешно.")

    if result["ok"]:
        return HTMLResponse(
            content='<div class="alert alert-success">Тестовое уведомление отправлено</div>'
        )

    error_text = result.get("error", "Неизвестная ошибка")
    return HTMLResponse(
        content=f'<div class="alert alert-error">Ошибка: {error_text}</div>'
    )
