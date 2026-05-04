from typing import Annotated
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, DeclarativeBase
from fastapi import Depends
from app.config import DATABASE_URL, SQL_ECHO

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=SQL_ECHO,
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


class Base(DeclarativeBase):
    pass


def create_db_tables():
    Base.metadata.create_all(engine)
    _migrate_licenses_to_assets()


def _migrate_licenses_to_assets() -> None:
    """v1.1 schema migration: rename old `licenses` table to `assets` and add
    new columns. Idempotent — safe to call on every startup.

    Legacy installs have a `licenses` table from v1.0. New installs only have
    `assets` (created by Base.metadata.create_all). When both exist (created
    side by side), copy rows from licenses → assets and drop licenses.
    """
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "licenses" not in tables:
        return

    legacy_cols = {col["name"] for col in inspector.get_columns("licenses")}
    asset_cols = {col["name"] for col in inspector.get_columns("assets")} if "assets" in tables else set()

    with engine.begin() as conn:
        legacy_count = conn.execute(text("SELECT COUNT(*) FROM licenses")).scalar() or 0
        asset_count = conn.execute(text("SELECT COUNT(*) FROM assets")).scalar() if "assets" in tables else 0

        if legacy_count == 0:
            # Empty legacy table — safe to drop unconditionally.
            conn.execute(text("DROP TABLE licenses"))
            return

        if asset_count > 0:
            # Both tables hold data — refuse to merge automatically. Operator
            # must reconcile manually. Leave both tables in place.
            return

        # Copy legacy rows → assets, then drop legacy table.
        shared = sorted(legacy_cols & asset_cols)
        cols_csv = ", ".join(shared)
        conn.execute(text(
            f"INSERT INTO assets ({cols_csv}, asset_type) "
            f"SELECT {cols_csv}, 'license' FROM licenses"
        ))
        conn.execute(text("DROP TABLE licenses"))


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def bootstrap_settings():
    """Seed non-secret defaults on first run.

    Telegram secrets (token, chat_id) are NEVER written to the DB — source of truth
    is .env (config module). Removes any pre-existing rows to migrate older installs.
    """
    from app.models import AppSettings

    with Session(engine) as db:
        # Migration: drop secrets that older versions wrote to DB
        db.query(AppSettings).filter(
            AppSettings.key.in_(["telegram_bot_token", "telegram_chat_id"])
        ).delete(synchronize_session=False)

        existing_keys = {row.key for row in db.query(AppSettings).all()}
        for key, value in [
            ("notify_days_before", "60"),
            ("notifications_enabled", "true"),
        ]:
            if key not in existing_keys:
                db.add(AppSettings(key=key, value=value))
        db.commit()
