from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.database import Base
from app.models import AppSettings, License


@pytest.fixture
def test_engine():
    """In-memory SQLite engine for unit tests."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def test_session(test_engine):
    """Session bound to in-memory test engine."""
    with Session(test_engine) as session:
        yield session


@pytest.fixture
def make_license(test_session):
    """Factory fixture to create License instances with sensible defaults."""

    def _make(product_name="Test Product", days_until=30, notify_days_before=None):
        lic = License(
            product_name=product_name,
            purchase_date=date.today() - timedelta(days=365),
            expiry_date=date.today() + timedelta(days=days_until),
            responsible="Test User",
            notify_days_before=notify_days_before,
        )
        test_session.add(lic)
        test_session.commit()
        test_session.refresh(lic)
        return lic

    return _make


@pytest.fixture
def seed_default_settings(test_session):
    """Seed the notify_days_before app setting with value 60."""
    setting = AppSettings(key="notify_days_before", value="60")
    test_session.add(setting)
    test_session.commit()
