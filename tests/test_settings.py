"""Integration tests for settings routes (SETT-01, SETT-03, NOTF-04, NOTF-06)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base, get_session
from app.models import AppSettings, License  # noqa: F401


# ---------- module-level engine (StaticPool keeps same connection for TestClient) ----------

test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(test_engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


Base.metadata.create_all(test_engine)


def _override_get_session():
    with Session(test_engine) as session:
        yield session


from app.main import app  # noqa: E402 -- after engine setup


@pytest.fixture(autouse=True)
def _clean_tables():
    """Wipe all rows before each test so tests are isolated."""
    with Session(test_engine) as session:
        session.query(AppSettings).delete()
        session.commit()
    yield


@pytest.fixture
def client():
    """TestClient with DB session overridden to use in-memory test DB."""
    previous = app.dependency_overrides.get(get_session)
    app.dependency_overrides[get_session] = _override_get_session
    yield TestClient(app)
    if previous is not None:
        app.dependency_overrides[get_session] = previous
    else:
        app.dependency_overrides.pop(get_session, None)


# ---------- tests ----------

def test_settings_page_renders(client):
    """GET /settings returns 200 with non-secret form fields and Telegram status block. Covers SETT-01."""
    response = client.get("/settings")
    assert response.status_code == 200
    body = response.text
    assert "Настройки" in body
    assert "notify_days_before" in body
    assert "notify_time" in body
    # Telegram status block present (read-only); secrets not in form inputs
    assert "Telegram" in body
    assert 'name="bot_token"' not in body
    assert 'name="chat_id"' not in body


def test_save_settings(client):
    """POST /settings saves non-secret fields. Covers SETT-03, NOTF-04, NOTF-06."""
    response = client.post(
        "/settings",
        data={
            "notify_days_before": "30",
            "notify_time": "10:00",
        },
    )
    assert response.status_code == 200

    get_response = client.get("/settings")
    assert get_response.status_code == 200
    body = get_response.text
    assert "30" in body
    assert "10:00" in body


def test_settings_persist_across_requests(client):
    """POST saves values; subsequent GET still returns them. Covers SETT-03 persistence."""
    client.post(
        "/settings",
        data={
            "notify_days_before": "45",
            "notify_time": "08:30",
        },
    )
    response = client.get("/settings")
    assert response.status_code == 200
    body = response.text
    assert "45" in body
    assert "08:30" in body


def test_save_settings_invalid_threshold(client):
    """POST /settings with non-integer threshold returns 200 with error. Covers validation."""
    response = client.post(
        "/settings",
        data={
            "notify_days_before": "abc",
            "notify_time": "09:00",
        },
    )
    assert response.status_code == 200
    body = response.text
    assert "notify_days_before" in body
    with Session(test_engine) as session:
        rows = session.query(AppSettings).all()
    assert len(rows) == 0


def test_save_settings_invalid_time(client):
    """POST /settings with invalid time (25:00) returns 200 with error. Covers validation."""
    response = client.post(
        "/settings",
        data={
            "notify_days_before": "30",
            "notify_time": "25:00",
        },
    )
    assert response.status_code == 200
    body = response.text
    assert "notify_time" in body
    with Session(test_engine) as session:
        rows = session.query(AppSettings).all()
    assert len(rows) == 0


def test_settings_nav_link(client):
    """GET / (dashboard) includes nav link to /settings. Covers nav integration."""
    response = client.get("/")
    assert response.status_code == 200
    body = response.text
    assert 'href="/settings"' in body
    assert "Настройки" in body


def test_settings_db_over_env_precedence(client):
    """POST saves notify_days_before=45; DB confirms value is '45'. Covers SETT-03 DB precedence."""
    client.post(
        "/settings",
        data={
            "notify_days_before": "45",
            "notify_time": "09:00",
        },
    )
    with Session(test_engine) as session:
        row = session.query(AppSettings).filter(AppSettings.key == "notify_days_before").first()
    assert row is not None
    assert row.value == "45"


# ---------- test notification tests (SETT-02) ----------

def test_test_notification_success(client, monkeypatch):
    """POST /settings/test-notification with valid env credentials sends message. Covers SETT-02."""
    from unittest.mock import patch

    monkeypatch.setattr("app.routers.settings.TELEGRAM_BOT_TOKEN", "tok123")
    monkeypatch.setattr("app.routers.settings.TELEGRAM_CHAT_ID", "-100")

    with patch("app.routers.settings.send_telegram_message", return_value={"ok": True}):
        response = client.post("/settings/test-notification")

    assert response.status_code == 200
    assert "Тестовое уведомление отправлено" in response.text


def test_test_notification_no_credentials(client, monkeypatch):
    """POST /settings/test-notification without env credentials shows error. Covers SETT-02 error case."""
    monkeypatch.setattr("app.routers.settings.TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setattr("app.routers.settings.TELEGRAM_CHAT_ID", "")

    response = client.post("/settings/test-notification")

    assert response.status_code == 200
    assert "Сначала настройте" in response.text


def test_test_notification_telegram_error(client, monkeypatch):
    """POST /settings/test-notification with Telegram API error shows error message. Covers SETT-02."""
    from unittest.mock import patch

    monkeypatch.setattr("app.routers.settings.TELEGRAM_BOT_TOKEN", "bad_token")
    monkeypatch.setattr("app.routers.settings.TELEGRAM_CHAT_ID", "-100")

    with patch(
        "app.routers.settings.send_telegram_message",
        return_value={"ok": False, "error": "Неверный токен бота", "error_code": 401},
    ):
        response = client.post("/settings/test-notification")

    assert response.status_code == 200
    assert "Ошибка" in response.text
    assert "Неверный токен бота" in response.text
