"""APScheduler daily digest job — starts in FastAPI lifespan, reschedules on settings save."""

from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TZ
from app.database import engine
from app.models import AppSettings, License
from app.services.status import enrich_licenses, get_global_threshold
from app.services.telegram import format_digest, send_telegram_message

scheduler = BackgroundScheduler(timezone=ZoneInfo(TZ))


def send_daily_digest() -> None:
    """Scheduled job — runs in APScheduler thread, creates own DB session.

    Telegram secrets read from env (config), never from DB.
    """
    token = TELEGRAM_BOT_TOKEN
    chat_id = TELEGRAM_CHAT_ID

    # D-11: silently skip when bot_token or chat_id not configured
    if not token or not chat_id:
        return

    with Session(engine) as db:
        threshold = get_global_threshold(db)
        licenses = db.query(License).all()
        enriched = enrich_licenses(licenses, threshold)

        # D-04: send nothing if no qualifying licenses
        message = format_digest(enriched)
        if message is None:
            return

        result = send_telegram_message(token, chat_id, message)

        if result.get("ok"):
            row = db.query(AppSettings).filter(AppSettings.key == "last_digest_sent").first()
            if row is not None:
                row.value = datetime.now().isoformat()
            else:
                db.add(AppSettings(key="last_digest_sent", value=datetime.now().isoformat()))
            db.commit()


def init_scheduler(hour: int = 9, minute: int = 0) -> None:
    """Add daily_digest job and start scheduler (guards against double-start)."""
    scheduler.add_job(
        send_daily_digest,
        trigger=CronTrigger(hour=hour, minute=minute, timezone=ZoneInfo(TZ)),
        id="daily_digest",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    if not scheduler.running:
        scheduler.start()


def reschedule_digest(hour: int, minute: int) -> None:
    """Update the daily_digest fire time without restarting the scheduler (D-07)."""
    scheduler.reschedule_job(
        "daily_digest",
        trigger=CronTrigger(hour=hour, minute=minute, timezone=ZoneInfo(TZ)),
    )


def shutdown_scheduler() -> None:
    """Gracefully stop the scheduler on app shutdown."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
