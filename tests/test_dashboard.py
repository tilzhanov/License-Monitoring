"""Integration tests for dashboard routes (DASH-01 through DASH-04, LIC-05)."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base, get_session
from app.models import AppSettings, License  # noqa: F401


# ---------- fixtures ----------

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
        session.query(License).delete()
        session.query(AppSettings).delete()
        session.commit()
    yield


@pytest.fixture
def client():
    """TestClient with DB session overridden to use in-memory test DB."""
    previous = app.dependency_overrides.get(get_session)
    app.dependency_overrides[get_session] = _override_get_session
    yield TestClient(app)
    # Restore previous override (from test_health.py module-level) instead of clearing
    if previous is not None:
        app.dependency_overrides[get_session] = previous
    else:
        app.dependency_overrides.pop(get_session, None)


@pytest.fixture
def seeded_db():
    """Seed test DB with licenses in all three statuses + default settings."""
    with Session(test_engine) as session:
        session.add(AppSettings(key="notify_days_before", value="30"))

        # Active license (expires in 60 days, threshold 30)
        session.add(License(
            product_name="vCenter Active",
            purchase_date=date.today() - timedelta(days=365),
            expiry_date=date.today() + timedelta(days=60),
            responsible="Иванов",
        ))
        # Warning license (expires in 15 days, threshold 30)
        session.add(License(
            product_name="Veeam Warning",
            purchase_date=date.today() - timedelta(days=365),
            expiry_date=date.today() + timedelta(days=15),
            responsible="Петров",
        ))
        # Expired license (expired 5 days ago)
        session.add(License(
            product_name="vCloud Expired",
            purchase_date=date.today() - timedelta(days=365),
            expiry_date=date.today() - timedelta(days=5),
            responsible="Сидоров",
        ))
        session.commit()


# ---------- Dashboard page tests ----------


def test_dashboard_empty_db(client):
    """GET / with no licenses shows empty state message."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Пока нет активов" in response.text


def test_stats_counters(client, seeded_db):
    """GET / shows correct stats: total=3, expiring=1, expired=1 (DASH-01)."""
    response = client.get("/")
    assert response.status_code == 200
    text = response.text
    # stat-card total should show 3
    assert ">3<" in text
    # stat-card warning should show 1
    # stat-card expired should show 1
    assert 'class="stat-card warning"' in text or "stat-card warning" in text
    assert 'class="stat-card expired"' in text or "stat-card expired" in text


def test_expiring_soon_widget(client, seeded_db):
    """GET / expiring-soon widget contains warning license (DASH-02)."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Veeam Warning" in response.text
    assert "expiring-widget" in response.text


def test_status_color_classes(client, seeded_db):
    """GET / table rows have color-coded CSS classes (DASH-03)."""
    response = client.get("/")
    assert response.status_code == 200
    text = response.text
    assert "status-expired" in text
    assert "status-warning" in text
    assert "status-active" in text


def test_no_expired_in_expiring_widget(client, seeded_db):
    """Expired licenses should NOT appear in the expiring-soon widget."""
    response = client.get("/")
    text = response.text
    # The expiring widget section ends before the table; vCloud Expired
    # should only appear in the table, not in the widget list items.
    widget_section = text.split("expiring-widget")[1].split("</section>")[0]
    assert "vCloud Expired" not in widget_section


# ---------- Partial endpoint tests (DASH-04) ----------


def test_table_partial_endpoint(client, seeded_db):
    """GET /licenses/table returns 200 with <tr> rows."""
    response = client.get("/licenses/table")
    assert response.status_code == 200
    assert "<tr" in response.text
    assert "vCenter Active" in response.text
    assert "Veeam Warning" in response.text
    assert "vCloud Expired" in response.text


def test_filter_by_product(client, seeded_db):
    """GET /licenses/table?product=vCenter returns only matching row."""
    response = client.get("/licenses/table?product=vCenter")
    assert response.status_code == 200
    assert "vCenter Active" in response.text
    assert "Veeam Warning" not in response.text
    assert "vCloud Expired" not in response.text


def test_filter_by_product_case_insensitive(client, seeded_db):
    """Product filter is case-insensitive."""
    response = client.get("/licenses/table?product=vcenter")
    assert response.status_code == 200
    assert "vCenter Active" in response.text


def test_filter_by_status(client, seeded_db):
    """GET /licenses/table?status=expired returns only expired row."""
    response = client.get("/licenses/table?status=expired")
    assert response.status_code == 200
    assert "vCloud Expired" in response.text
    assert "vCenter Active" not in response.text
    assert "Veeam Warning" not in response.text


def test_filter_by_status_warning(client, seeded_db):
    """GET /licenses/table?status=warning returns only warning row."""
    response = client.get("/licenses/table?status=warning")
    assert response.status_code == 200
    assert "Veeam Warning" in response.text
    assert "vCenter Active" not in response.text


def test_sort_by_product_name(client, seeded_db):
    """GET /licenses/table?sort=product_name&order=asc returns alphabetical order."""
    response = client.get("/licenses/table?sort=product_name&order=asc")
    assert response.status_code == 200
    text = response.text
    # Lowercase sort: vcenter < vcloud < veeam (vc < vc < ve)
    pos_vcenter = text.index("vCenter Active")
    pos_vcloud = text.index("vCloud Expired")
    pos_veeam = text.index("Veeam Warning")
    assert pos_vcenter < pos_vcloud < pos_veeam


def test_sort_by_expiry_desc(client, seeded_db):
    """GET /licenses/table?sort=expiry_date&order=desc returns active first, expired last."""
    response = client.get("/licenses/table?sort=expiry_date&order=desc")
    assert response.status_code == 200
    text = response.text
    pos_active = text.index("vCenter Active")
    pos_warning = text.index("Veeam Warning")
    pos_expired = text.index("vCloud Expired")
    assert pos_active < pos_warning < pos_expired


def test_combined_filter_and_sort(client, seeded_db):
    """Combined filter and sort works together."""
    response = client.get("/licenses/table?status=active&sort=product_name&order=asc")
    assert response.status_code == 200
    assert "vCenter Active" in response.text
    assert "Veeam Warning" not in response.text
    assert "vCloud Expired" not in response.text


def test_htmx_attributes_on_index(client, seeded_db):
    """GET / contains HTMX attributes for filter/sort (DASH-04)."""
    response = client.get("/")
    assert response.status_code == 200
    text = response.text
    assert 'hx-get="/licenses/table"' in text
    assert 'hx-target="#license-tbody"' in text
    assert "hx-include=" in text
    assert 'hx-trigger="keyup changed delay:300ms"' in text
    assert 'hx-trigger="change"' in text
