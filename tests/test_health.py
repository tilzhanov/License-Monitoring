import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.database import Base, get_session
from app.models import License, AppSettings  # noqa: F401 -- register models

# Create a test engine that overrides the production engine
# StaticPool ensures all connections share the same in-memory database
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


def override_get_session():
    with Session(test_engine) as session:
        yield session


# Import app AFTER setting up overrides
from app.main import app
app.dependency_overrides[get_session] = override_get_session

client = TestClient(app)


def test_health_returns_200():
    """GET /health returns 200 (INFRA-01)."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_returns_json():
    """GET /health returns {"status": "ok"}."""
    response = client.get("/health")
    assert response.json() == {"status": "ok"}


def test_index_returns_200():
    """GET / returns 200."""
    response = client.get("/")
    assert response.status_code == 200


def test_index_returns_html():
    """GET / returns HTML content."""
    response = client.get("/")
    assert "text/html" in response.headers["content-type"]


def test_index_contains_title():
    """GET / HTML contains License Monitor title."""
    response = client.get("/")
    assert "License Monitor" in response.text


def test_index_contains_htmx():
    """GET / HTML includes HTMX script tag."""
    response = client.get("/")
    assert "htmx.org" in response.text


def test_static_css_served():
    """Static CSS file is accessible at /static/css/app.css."""
    response = client.get("/static/css/app.css")
    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]
