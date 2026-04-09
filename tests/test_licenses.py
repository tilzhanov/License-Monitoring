"""Integration tests for license CRUD operations (LIC-01, LIC-02, LIC-03, DASH-05)."""

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
        # Seed default threshold for status computation
        session.add(AppSettings(key="notify_days_before", value="30"))
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


@pytest.fixture
def sample_license():
    """Create a sample license directly in the DB."""
    with Session(test_engine) as session:
        lic = License(
            product_name="vCenter 7.0",
            purchase_date=date(2025, 1, 1),
            expiry_date=date.today() + timedelta(days=90),
            responsible="Иванов И.И.",
            cost="500 000 тенге",
            comment="Тестовая лицензия",
        )
        session.add(lic)
        session.commit()
        session.refresh(lic)
        return lic


# --- Create ---


def test_new_license_page(client):
    resp = client.get("/licenses/new")
    assert resp.status_code == 200
    assert "Новая лицензия" in resp.text


def test_create_license_success(client):
    resp = client.post("/licenses", data={
        "product_name": "Veeam Backup",
        "purchase_date": "2025-01-01",
        "expiry_date": "2026-12-31",
        "responsible": "Петров П.П.",
        "cost": "1 000 000 тенге",
        "comment": "Годовая лицензия",
    }, follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/"
    with Session(test_engine) as session:
        lic = session.query(License).filter_by(product_name="Veeam Backup").first()
        assert lic is not None
        assert lic.expiry_date == date(2026, 12, 31)


def test_create_license_validation_missing_product(client):
    resp = client.post("/licenses", data={
        "product_name": "",
        "purchase_date": "2025-01-01",
        "expiry_date": "2026-12-31",
    })
    assert resp.status_code == 200
    assert "Укажите название продукта" in resp.text


def test_create_license_validation_missing_dates(client):
    resp = client.post("/licenses", data={
        "product_name": "Test",
        "purchase_date": "",
        "expiry_date": "",
    })
    assert resp.status_code == 200
    assert "Укажите дату покупки" in resp.text
    assert "Укажите дату истечения" in resp.text


def test_create_license_validation_expiry_before_purchase(client):
    resp = client.post("/licenses", data={
        "product_name": "Test",
        "purchase_date": "2026-06-01",
        "expiry_date": "2025-01-01",
    })
    assert resp.status_code == 200
    assert "Дата истечения не может быть раньше даты покупки" in resp.text


def test_create_license_preserves_form_values(client):
    resp = client.post("/licenses", data={
        "product_name": "",
        "purchase_date": "2025-03-15",
        "expiry_date": "2026-06-30",
        "responsible": "Сидоров",
        "cost": "100 000",
        "comment": "Тест",
    })
    assert resp.status_code == 200
    assert "2025-03-15" in resp.text
    assert "2026-06-30" in resp.text


# --- Edit ---


def test_edit_license_page(client, sample_license):
    resp = client.get(f"/licenses/{sample_license.id}/edit")
    assert resp.status_code == 200
    assert "Редактирование лицензии" in resp.text
    assert "vCenter 7.0" in resp.text


def test_update_license_success(client, sample_license):
    resp = client.post(f"/licenses/{sample_license.id}", data={
        "product_name": "vCenter 8.0",
        "purchase_date": "2025-06-01",
        "expiry_date": "2027-06-01",
        "responsible": "Сидоров С.С.",
        "cost": "750 000 тенге",
        "comment": "Обновлённая лицензия",
    }, follow_redirects=False)
    assert resp.status_code == 303
    with Session(test_engine) as session:
        lic = session.get(License, sample_license.id)
        assert lic.product_name == "vCenter 8.0"


def test_edit_nonexistent_license(client):
    resp = client.get("/licenses/99999/edit")
    assert resp.status_code == 404


# --- Delete ---


def test_delete_license(client, sample_license):
    resp = client.delete(f"/licenses/{sample_license.id}")
    assert resp.status_code == 200
    with Session(test_engine) as session:
        assert session.get(License, sample_license.id) is None


def test_delete_nonexistent_license(client):
    resp = client.delete("/licenses/99999")
    assert resp.status_code == 404


# --- Detail ---


def test_detail_page(client, sample_license):
    resp = client.get(f"/licenses/{sample_license.id}")
    assert resp.status_code == 200
    assert "vCenter 7.0" in resp.text
    assert "Иванов И.И." in resp.text
    assert "500 000 тенге" in resp.text


def test_detail_nonexistent(client):
    resp = client.get("/licenses/99999")
    assert resp.status_code == 404
    assert "Лицензия не найдена" in resp.text
