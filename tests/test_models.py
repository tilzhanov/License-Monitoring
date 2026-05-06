from datetime import date
from sqlalchemy import event, inspect, text
from sqlalchemy.orm import Session
from app.models import License, AppSettings
from app.database import Base


def test_assets_table_exists(test_engine):
    """assets table replaces licenses in v1.1; License is alias for Asset."""
    inspector = inspect(test_engine)
    names = inspector.get_table_names()
    assert "assets" in names
    assert "licenses" not in names


def test_assets_columns(test_engine):
    """assets table contains common + support type-specific columns."""
    inspector = inspect(test_engine)
    columns = {col["name"] for col in inspector.get_columns("assets")}
    expected = {
        "id", "product_id", "asset_type",
        "product_name", "purchase_date", "expiry_date",
        "responsible", "cost", "comment", "notify_days_before",
        "document_url",
        "support_contract_no",
        "created_at", "updated_at",
    }
    assert expected == columns


def test_assets_not_null_columns(test_engine):
    """product_name, expiry_date, asset_type are NOT NULL."""
    inspector = inspect(test_engine)
    columns = {col["name"]: col["nullable"] for col in inspector.get_columns("assets")}
    assert columns["product_name"] is False
    assert columns["expiry_date"] is False
    assert columns["asset_type"] is False


def test_assets_nullable_columns(test_engine):
    """purchase_date is now nullable."""
    inspector = inspect(test_engine)
    columns = {col["name"]: col["nullable"] for col in inspector.get_columns("assets")}
    assert columns["purchase_date"] is True
    assert columns["responsible"] is True
    assert columns["cost"] is True
    assert columns["comment"] is True
    assert columns["notify_days_before"] is True
    assert columns["product_id"] is True


def test_license_insert_required_only(test_session):
    """License (alias for Asset) can be inserted with only required fields."""
    lic = License(
        product_name="vSphere",
        purchase_date=date(2024, 1, 1),
        expiry_date=date(2025, 1, 1),
    )
    test_session.add(lic)
    test_session.commit()
    test_session.refresh(lic)

    assert lic.id is not None
    assert lic.product_name == "vSphere"
    assert lic.asset_type == "license"
    assert lic.responsible is None
    assert lic.cost is None
    assert lic.comment is None
    assert lic.notify_days_before is None


def test_app_settings_table_exists(test_engine):
    """app_settings table is created by create_all."""
    inspector = inspect(test_engine)
    assert "app_settings" in inspector.get_table_names()


def test_app_settings_columns(test_engine):
    """app_settings table has key (PK) and value columns."""
    inspector = inspect(test_engine)
    columns = {col["name"] for col in inspector.get_columns("app_settings")}
    assert columns == {"key", "value"}


def test_app_settings_key_is_primary(test_engine):
    """app_settings.key is the primary key."""
    inspector = inspect(test_engine)
    pk = inspector.get_pk_constraint("app_settings")
    assert pk["constrained_columns"] == ["key"]


def test_wal_mode(tmp_path):
    """WAL journal mode is set on file-based SQLite engine."""
    from sqlalchemy import create_engine as ce
    db_path = tmp_path / "test_wal.db"
    eng = ce(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})

    @event.listens_for(eng, "connect")
    def _set_wal(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

    # Trigger a connection to fire the pragma
    with eng.connect() as conn:
        result = conn.execute(text("PRAGMA journal_mode")).scalar()
        assert result == "wal"
    eng.dispose()


def test_bootstrap_settings_inserts_non_secret_defaults(test_engine, monkeypatch):
    """bootstrap_settings() writes only non-secret defaults; secrets stay in .env."""
    monkeypatch.setattr("app.database.engine", test_engine)

    from app.database import bootstrap_settings
    bootstrap_settings()

    with Session(test_engine) as session:
        rows = session.query(AppSettings).all()
        keys = {r.key: r.value for r in rows}

    assert "telegram_bot_token" not in keys
    assert "telegram_chat_id" not in keys
    assert keys["notify_days_before"] == "60"
    assert keys["notifications_enabled"] == "true"


def test_bootstrap_settings_purges_legacy_secrets(test_engine, monkeypatch):
    """bootstrap_settings() removes telegram_* rows written by older versions."""
    monkeypatch.setattr("app.database.engine", test_engine)

    with Session(test_engine) as session:
        session.add(AppSettings(key="telegram_bot_token", value="legacy-token"))
        session.add(AppSettings(key="telegram_chat_id", value="-100"))
        session.add(AppSettings(key="notify_days_before", value="45"))
        session.commit()

    from app.database import bootstrap_settings
    bootstrap_settings()

    with Session(test_engine) as session:
        rows = session.query(AppSettings).all()
        keys = {r.key: r.value for r in rows}

    assert "telegram_bot_token" not in keys
    assert "telegram_chat_id" not in keys
    assert keys["notify_days_before"] == "45"  # user value preserved
    assert keys["notifications_enabled"] == "true"  # default added
