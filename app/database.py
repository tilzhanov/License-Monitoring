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
