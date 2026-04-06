import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from app.database import Base


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
