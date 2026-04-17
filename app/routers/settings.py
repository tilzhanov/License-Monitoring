import re

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.config import NOTIFY_DAYS_BEFORE, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from app.database import SessionDep
from app.models import AppSettings
from app.templates import templates

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


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, db: SessionDep):
    """Render settings page with current values from DB (falling back to env/defaults)."""
    bot_token = get_setting(db, "telegram_bot_token", TELEGRAM_BOT_TOKEN)
    chat_id = get_setting(db, "telegram_chat_id", TELEGRAM_CHAT_ID)
    notify_days_before = get_setting(db, "notify_days_before", str(NOTIFY_DAYS_BEFORE))
    notify_time = get_setting(db, "notify_time", "09:00")

    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            "bot_token": bot_token,
            "chat_id": chat_id,
            "notify_days_before": notify_days_before,
            "notify_time": notify_time,
            "errors": {},
            "success": False,
            "success_message": "",
        },
    )


@router.post("/settings", response_class=HTMLResponse)
def save_settings(
    request: Request,
    db: SessionDep,
    bot_token: str = Form(""),
    chat_id: str = Form(""),
    notify_days_before: str = Form("60"),
    notify_time: str = Form("09:00"),
):
    """Save settings to AppSettings table; return HTMX-swappable form fragment."""
    errors: dict[str, str] = {}

    # Validate notify_days_before: must be a positive integer
    try:
        days_val = int(notify_days_before)
        if days_val <= 0:
            raise ValueError
    except (ValueError, TypeError):
        errors["notify_days_before"] = "Укажите положительное целое число"

    # Validate notify_time: must match HH:MM with valid hour (0-23) and minute (0-59)
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
                "bot_token": bot_token,
                "chat_id": chat_id,
                "notify_days_before": notify_days_before,
                "notify_time": notify_time,
                "errors": errors,
                "success": False,
                "success_message": "",
            },
        )

    save_setting(db, "telegram_bot_token", bot_token)
    save_setting(db, "telegram_chat_id", chat_id)
    save_setting(db, "notify_days_before", notify_days_before)
    save_setting(db, "notify_time", notify_time)

    return templates.TemplateResponse(
        request=request,
        name="partials/settings_form.html",
        context={
            "bot_token": bot_token,
            "chat_id": chat_id,
            "notify_days_before": notify_days_before,
            "notify_time": notify_time,
            "errors": {},
            "success": True,
            "success_message": "Настройки сохранены",
        },
    )
