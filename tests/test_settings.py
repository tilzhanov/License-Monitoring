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
    """GET /settings returns 200 with all four form fields. Covers SETT-01."""
    response = client.get("/settings")
    assert response.status_code == 200
    body = response.text
    assert "Настройки" in body
    assert "bot_token" in body
    assert "chat_id" in body
    assert "notify_days_before" in body
    assert "notify_time" in body


def test_save_settings(client):
    """POST /settings saves all four fields; GET /settings returns saved values. Covers SETT-03, NOTF-04, NOTF-06."""
    response = client.post(
        "/settings",
        data={
            "bot_token": "test123",
            "chat_id": "-100",
            "notify_days_before": "30",
            "notify_time": "10:00",
        },
    )
    assert response.status_code == 200

    get_response = client.get("/settings")
    assert get_response.status_code == 200
    body = get_response.text
    assert "test123" in body
    assert "-100" in body
    assert "30" in body
    assert "10:00" in body


def test_settings_persist_across_requests(client):
    """POST saves values; subsequent GET still returns them. Covers SETT-03 persistence."""
    client.post(
        "/settings",
        data={
            "bot_token": "persistent-token",
            "chat_id": "-999",
            "notify_days_before": "45",
            "notify_time": "08:30",
        },
    )
    response = client.get("/settings")
    assert response.status_code == 200
    body = response.text
    assert "persistent-token" in body
    assert "-999" in body
    assert "45" in body
    assert "08:30" in body


def test_save_settings_invalid_threshold(client):
    """POST /settings with non-integer threshold returns 200 with error. Covers validation."""
    response = client.post(
        "/settings",
        data={
            "bot_token": "tok",
            "chat_id": "-1",
            "notify_days_before": "abc",
            "notify_time": "09:00",
        },
    )
    assert response.status_code == 200
    # Should contain an error message about notify_days_before
    body = response.text
    assert "notify_days_before" in body
    # Values not saved — DB should remain empty
    with Session(test_engine) as session:
        rows = session.query(AppSettings).all()
    assert len(rows) == 0


def test_save_settings_invalid_time(client):
    """POST /settings with invalid time (25:00) returns 200 with error. Covers validation."""
    response = client.post(
        "/settings",
        data={
            "bot_token": "tok",
            "chat_id": "-1",
            "notify_days_before": "30",
            "notify_time": "25:00",
        },
    )
    assert response.status_code == 200
    body = response.text
    assert "notify_time" in body
    # Values not saved
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
            "bot_token": "any",
            "chat_id": "-1",
            "notify_days_before": "45",
            "notify_time": "09:00",
        },
    )
    with Session(test_engine) as session:
        row = session.query(AppSettings).filter(AppSettings.key == "notify_days_before").first()
    assert row is not None
    assert row.value == "45"


# ---------- test notification tests (SETT-02) ----------

def test_test_notification_success(client):
    """POST /settings/test-notification with valid credentials sends message. Covers SETT-02."""
    from unittest.mock import patch

    with Session(test_engine) as session:
        session.add(AppSettings(key="telegram_bot_token", value="tok123"))
        session.add(AppSettings(key="telegram_chat_id", value="-100"))
        session.commit()

    with patch("app.routers.settings.send_telegram_message", return_value={"ok": True}):
        response = client.post("/settings/test-notification")

    assert response.status_code == 200
    assert "Тестовое уведомление отправлено" in response.text


def test_test_notification_no_credentials(client):
    """POST /settings/test-notification without credentials shows error. Covers SETT-02 error case."""
    response = client.post("/settings/test-notification")

    assert response.status_code == 200
    assert "Сначала настройте" in response.text


def test_test_notification_telegram_error(client):
    """POST /settings/test-notification with Telegram error shows error message. Covers SETT-02."""
    from unittest.mock import patch

    with Session(test_engine) as session:
        session.add(AppSettings(key="telegram_bot_token", value="bad_token"))
        session.add(AppSettings(key="telegram_chat_id", value="-100"))
        session.commit()

    with patch(
        "app.routers.settings.send_telegram_message",
        return_value={"ok": False, "error": "Неверный токен бота", "error_code": 401},
    ):
        response = client.post("/settings/test-notification")

    assert response.status_code == 200
    assert "Ошибка" in response.text
    assert "Неверный токен бота" in response.text
