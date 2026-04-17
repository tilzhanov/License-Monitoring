"""APScheduler daily digest job — starts in FastAPI lifespan, reschedules on settings save."""

from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.database import engine
from app.models import AppSettings, License
from app.services.status import enrich_licenses, get_global_threshold
from app.services.telegram import format_digest, send_telegram_message

scheduler = BackgroundScheduler()


def _get_setting(db: Session, key: str) -> str:
    """Query AppSettings by key; return value string or empty string."""
    row = db.query(AppSettings).filter(AppSettings.key == key).first()
    if row is not None and row.value:
        return row.value
    return ""


def send_daily_digest() -> None:
    """Scheduled job — runs in APScheduler thread, creates own DB session.

    CRITICAL: Creates Session(engine) directly (NOT request-scoped get_session)
    to avoid thread-safety issues per Pitfall 1 in research notes.
    """
    with Session(engine) as db:
        token = _get_setting(db, "telegram_bot_token")
        chat_id = _get_setting(db, "telegram_chat_id")

        # D-11: silently skip when bot_token or chat_id not configured
        if not token or not chat_id:
            return

        threshold = get_global_threshold(db)
        licenses = db.query(License).all()
        enriched = enrich_licenses(licenses, threshold)

        # D-04: send nothing if no qualifying licenses
        message = format_digest(enriched)
        if message is None:
            return

        result = send_telegram_message(token, chat_id, message)

        if result.get("ok"):
            # Store last-sent timestamp (discretion item: visible on Settings page)
            row = db.query(AppSettings).filter(AppSettings.key == "last_digest_sent").first()
            if row is not None:
                row.value = datetime.now().isoformat()
            else:
                db.add(AppSettings(key="last_digest_sent", value=datetime.now().isoformat()))
            db.commit()


def init_scheduler(hour: int = 9, minute: int = 0) -> None:
    """Add daily_digest job and start scheduler (guards against double-start per Pitfall 2)."""
    scheduler.add_job(
        send_daily_digest,
        trigger=CronTrigger(hour=hour, minute=minute),
        id="daily_digest",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    # Guard: do not call start() if already running (prevents SchedulerAlreadyRunningError)
    if not scheduler.running:
        scheduler.start()


def reschedule_digest(hour: int, minute: int) -> None:
    """Update the daily_digest fire time without restarting the scheduler (D-07)."""
    scheduler.reschedule_job(
        "daily_digest",
        trigger=CronTrigger(hour=hour, minute=minute),
    )


def shutdown_scheduler() -> None:
    """Gracefully stop the scheduler on app shutdown."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
