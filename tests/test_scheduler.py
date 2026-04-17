"""Unit tests for the APScheduler daily digest scheduler.

All DB calls are redirected to an in-memory SQLite engine.
All external calls (Telegram) are mocked via unittest.mock.patch.
"""

from datetime import date, timedelta
from unittest.mock import MagicMock, call, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.models import AppSettings, License
from app.services.scheduler import (
    init_scheduler,
    reschedule_digest,
    send_daily_digest,
)


# ---------------------------------------------------------------------------
# In-memory engine fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def scheduler_engine():
    """In-memory SQLite engine with full schema for scheduler tests."""
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


def _seed(engine, settings: dict, licenses: list = None):
    """Helper: seed AppSettings and optional License rows."""
    with Session(engine) as db:
        for key, value in settings.items():
            db.add(AppSettings(key=key, value=value))
        for lic_kwargs in (licenses or []):
            db.add(License(**lic_kwargs))
        db.commit()


# ---------------------------------------------------------------------------
# init_scheduler tests
# ---------------------------------------------------------------------------

def test_init_scheduler_starts():
    """init_scheduler adds daily_digest job and calls start() when not running."""
    mock_sched = MagicMock()
    mock_sched.running = False

    with patch("app.services.scheduler.scheduler", mock_sched):
        init_scheduler(9, 0)

    mock_sched.add_job.assert_called_once()
    call_kwargs = mock_sched.add_job.call_args
    assert call_kwargs.kwargs.get("id") == "daily_digest" or call_kwargs[1].get("id") == "daily_digest"
    mock_sched.start.assert_called_once()


def test_init_scheduler_no_double_start():
    """init_scheduler does NOT call start() when scheduler is already running (Pitfall 2 guard)."""
    mock_sched = MagicMock()
    mock_sched.running = True

    with patch("app.services.scheduler.scheduler", mock_sched):
        init_scheduler(9, 0)

    # add_job IS called (replace_existing=True updates the trigger)
    mock_sched.add_job.assert_called_once()
    # start() must NOT be called again
    mock_sched.start.assert_not_called()


# ---------------------------------------------------------------------------
# reschedule_digest tests
# ---------------------------------------------------------------------------

def test_reschedule_digest():
    """reschedule_digest calls scheduler.reschedule_job with the correct id and a CronTrigger."""
    from apscheduler.triggers.cron import CronTrigger

    mock_sched = MagicMock()

    with patch("app.services.scheduler.scheduler", mock_sched):
        reschedule_digest(10, 30)

    mock_sched.reschedule_job.assert_called_once()
    call_args = mock_sched.reschedule_job.call_args
    # First positional arg must be "daily_digest"
    assert call_args[0][0] == "daily_digest"
    # trigger kwarg must be a CronTrigger
    trigger = call_args[1].get("trigger") or call_args[0][1]
    assert isinstance(trigger, CronTrigger)


# ---------------------------------------------------------------------------
# send_daily_digest tests
# ---------------------------------------------------------------------------

def test_send_daily_digest_skips_no_token(scheduler_engine):
    """send_daily_digest returns early when bot_token is empty (D-11)."""
    _seed(scheduler_engine, {
        "telegram_bot_token": "",
        "telegram_chat_id": "-100123",
    })

    with patch("app.services.scheduler.engine", scheduler_engine), \
         patch("app.services.scheduler.send_telegram_message") as mock_send:
        send_daily_digest()

    mock_send.assert_not_called()


def test_send_daily_digest_skips_no_chat_id(scheduler_engine):
    """send_daily_digest returns early when chat_id is empty (D-11)."""
    _seed(scheduler_engine, {
        "telegram_bot_token": "valid_token",
        "telegram_chat_id": "",
    })

    with patch("app.services.scheduler.engine", scheduler_engine), \
         patch("app.services.scheduler.send_telegram_message") as mock_send:
        send_daily_digest()

    mock_send.assert_not_called()


def test_send_daily_digest_skips_empty_digest(scheduler_engine):
    """send_daily_digest sends nothing when no qualifying licenses exist (D-04)."""
    # Seed credentials but NO licenses in DB
    _seed(scheduler_engine, {
        "telegram_bot_token": "valid_token",
        "telegram_chat_id": "-100123",
        "notify_days_before": "30",
    })

    with patch("app.services.scheduler.engine", scheduler_engine), \
         patch("app.services.scheduler.send_telegram_message") as mock_send:
        send_daily_digest()

    mock_send.assert_not_called()


def test_send_daily_digest_sends_message(scheduler_engine):
    """send_daily_digest calls send_telegram_message with token, chat_id, and digest string."""
    expiry = date.today() + timedelta(days=5)  # within 30-day threshold → warning
    _seed(
        scheduler_engine,
        settings={
            "telegram_bot_token": "test_token",
            "telegram_chat_id": "-100456",
            "notify_days_before": "30",
        },
        licenses=[{
            "product_name": "vCenter 7.0",
            "purchase_date": date.today() - timedelta(days=365),
            "expiry_date": expiry,
            "responsible": "Иванов",
        }],
    )

    with patch("app.services.scheduler.engine", scheduler_engine), \
         patch("app.services.scheduler.send_telegram_message", return_value={"ok": True}) as mock_send:
        send_daily_digest()

    mock_send.assert_called_once()
    call_args = mock_send.call_args[0]
    assert call_args[0] == "test_token"
    assert call_args[1] == "-100456"
    assert isinstance(call_args[2], str)
    assert len(call_args[2]) > 0


def test_send_daily_digest_updates_last_sent_timestamp(scheduler_engine):
    """send_daily_digest stores last_digest_sent in AppSettings after successful send."""
    expiry = date.today() + timedelta(days=5)
    _seed(
        scheduler_engine,
        settings={
            "telegram_bot_token": "test_token",
            "telegram_chat_id": "-100456",
            "notify_days_before": "30",
        },
        licenses=[{
            "product_name": "Veeam Backup",
            "purchase_date": date.today() - timedelta(days=200),
            "expiry_date": expiry,
        }],
    )

    with patch("app.services.scheduler.engine", scheduler_engine), \
         patch("app.services.scheduler.send_telegram_message", return_value={"ok": True}):
        send_daily_digest()

    with Session(scheduler_engine) as db:
        row = db.query(AppSettings).filter_by(key="last_digest_sent").first()
    assert row is not None
    assert row.value  # non-empty ISO timestamp


def test_send_daily_digest_no_timestamp_on_failed_send(scheduler_engine):
    """send_daily_digest does NOT update last_digest_sent when Telegram returns error."""
    expiry = date.today() + timedelta(days=5)
    _seed(
        scheduler_engine,
        settings={
            "telegram_bot_token": "bad_token",
            "telegram_chat_id": "-100456",
            "notify_days_before": "30",
        },
        licenses=[{
            "product_name": "Veeam Backup",
            "purchase_date": date.today() - timedelta(days=200),
            "expiry_date": expiry,
        }],
    )

    with patch("app.services.scheduler.engine", scheduler_engine), \
         patch("app.services.scheduler.send_telegram_message", return_value={"ok": False, "error": "Unauthorized", "error_code": 401}):
        send_daily_digest()

    with Session(scheduler_engine) as db:
        row = db.query(AppSettings).filter_by(key="last_digest_sent").first()
    assert row is None
